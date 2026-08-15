use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

/// Holds the handle to the running `skelly-sync-api` child process so it can
/// be killed on app exit. A hard kill is acceptable: the API's job store is
/// in-memory/ephemeral and each sync job already runs in its own isolated
/// `multiprocessing.Process`, so there's no shared state to corrupt.
struct ApiProcess(Mutex<Option<CommandChild>>);

/// Resolves the user's actual login-shell `PATH` by asking their `$SHELL` to
/// print it (as a login shell, so `.zprofile`/`.profile`/etc. get sourced).
///
/// GUI apps launched via Finder/LaunchServices (double-click, `open`) get a
/// minimal default `PATH` (`/usr/bin:/bin:/usr/sbin:/sbin` plus a couple
/// system entries) that does NOT include Homebrew's `/opt/homebrew/bin` (or
/// any other install location a user's shell profile adds) -- this is a
/// well-known macOS quirk, distinct from `tauri dev`, which runs as a child
/// of an already PATH-rich Terminal shell. Without this, `skelly-sync-api`
/// starts fine but every ffmpeg/ffprobe subprocess call inside it fails with
/// `FileNotFoundError: ffprobe not found`, even though a Terminal-launched
/// process on the same machine works. Resolving via the user's own shell
/// (rather than hardcoding `/opt/homebrew/bin`) is robust to however
/// ffmpeg is actually installed (Homebrew Intel/ARM, MacPorts, manual, ...).
fn resolve_login_shell_path() -> Option<String> {
    const START: &str = "__SKELLY_PATH_START__";
    const END: &str = "__SKELLY_PATH_END__";
    let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".to_string());
    // `-l` (login, not `-i`/interactive) sources profile files without the
    // TTY/prompt behavior interactive shells can have, avoiding hang risk.
    let output = std::process::Command::new(&shell)
        // `${PATH}`, not `$PATH{END}` -- the latter parses as the (unset)
        // variable `PATH__SKELLY_PATH_END__` in both bash and zsh.
        .args(["-lc", &format!("echo {START}${{PATH}}{END}")])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8(output.stdout).ok()?;
    let start = text.find(START)? + START.len();
    let end = text.find(END)?;
    let path = text.get(start..end)?.trim();
    (!path.is_empty()).then(|| path.to_string())
}

fn spawn_api<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
) -> Result<CommandChild, Box<dyn std::error::Error>> {
    let shell = app.shell();
    let mut command = if cfg!(debug_assertions) {
        // Dev: run the API straight from the activated venv's PATH so
        // iteration doesn't require re-running PyInstaller on every change.
        shell.command("skelly-sync-api")
    } else {
        // Release: run the PyInstaller-frozen (onedir) binary bundled as a
        // plain resource under `bundle.resources` in tauri.conf.json, not a
        // `externalBin` sidecar -- onedir's directory-plus-`_internal/`
        // payload doesn't fit that convention's single-executable
        // assumption (see packaging/pyinstaller/skelly-sync-api.spec for
        // why onedir, not onefile, is used here). `resource_dir()` resolves
        // to `Contents/Resources` inside the .app bundle.
        let exe_path = app
            .path()
            .resource_dir()?
            .join("resources/skelly-sync-api/skelly-sync-api");
        shell.command(exe_path)
    };

    if let Some(path) = resolve_login_shell_path() {
        command = command.env("PATH", path);
    }

    let (mut rx, child) = command.spawn()?;

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

/// `CommandChild::kill()` only signals the direct child PID. Sweep for any
/// leftover sidecar processes by name as a best-effort backstop (e.g. the
/// per-job `multiprocessing.Process` and `multiprocessing.Manager` helper
/// processes it spawns) -- acceptable here since there's no shared state to
/// corrupt, see `ApiProcess`'s doc comment above.
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
            // Registered unconditionally (not just in dev): without a
            // logger backend, the `log::info!`/`log::warn!` calls in
            // `spawn_api`'s stdout/stderr reader are silently discarded in
            // release builds, so a sidecar crash traceback would otherwise
            // be captured and then thrown away. Defaults to logging to
            // both stdout and the platform log dir (`~/Library/Logs/<bundle
            // id>/` on macOS) -- see `tauri_plugin_log::Builder::default()`.
            app.handle().plugin(
                tauri_plugin_log::Builder::default()
                    .level(log::LevelFilter::Info)
                    .build(),
            )?;

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
