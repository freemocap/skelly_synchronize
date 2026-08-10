use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

/// Holds the handle to the running `skelly-sync-api` child process so it can
/// be killed on app exit. A hard kill is acceptable: the API's job store is
/// in-memory/ephemeral and each sync job already runs in its own isolated
/// `multiprocessing.Process`, so there's no shared state to corrupt.
struct ApiProcess(Mutex<Option<CommandChild>>);

fn spawn_api<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
) -> Result<CommandChild, Box<dyn std::error::Error>> {
    let shell = app.shell();
    let (mut rx, child) = if cfg!(debug_assertions) {
        // Dev: run the API straight from the activated venv's PATH so
        // iteration doesn't require re-running PyInstaller on every change.
        shell.command("skelly-sync-api").spawn()?
    } else {
        // Release: run the PyInstaller-frozen binary bundled as a sidecar
        // (registered under `bundle.externalBin` in tauri.conf.json).
        shell.sidecar("skelly-sync-api")?.spawn()?
    };

    tauri::async_runtime::spawn(async move {
        use tauri_plugin_shell::process::CommandEvent;
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    log::info!("[skelly-sync-api] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    log::warn!("[skelly-sync-api] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Error(err) => {
                    log::error!("[skelly-sync-api] process error: {err}");
                }
                CommandEvent::Terminated(payload) => {
                    log::warn!("[skelly-sync-api] exited: {payload:?}");
                }
                _ => {}
            }
        }
    });

    Ok(child)
}

/// `CommandChild::kill()` only signals the direct child PID. In release
/// builds the sidecar is a PyInstaller onefile binary whose bootloader forks
/// a grandchild that runs the actual server — killing just the bootloader
/// leaves that grandchild running. Sweep for any leftover sidecar processes
/// by name as a best-effort backstop (acceptable here: no shared state to
/// corrupt, see `ApiProcess`'s doc comment above).
fn kill_orphaned_sidecar_children() {
    let _ = std::process::Command::new("pkill")
        .args(["-9", "-f", "skelly-sync-api"])
        .status();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let child = spawn_api(app.handle())?;
            app.manage(ApiProcess(Mutex::new(Some(child))));

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = event {
                let state = app_handle.state::<ApiProcess>();
                let child = state.0.lock().unwrap().take();
                if let Some(child) = child {
                    let _ = child.kill();
                }
                kill_orphaned_sidecar_children();
            }
        });
}
