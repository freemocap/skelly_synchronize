import time

from skelly_synchronize.core.models import SyncMethod, SyncRequest, SyncResult
from skelly_synchronize.core.pipeline.stages import (
    AudioLagStage,
    BrightnessLagStage,
    DebugArtifactsStage,
    DiscoverVideosStage,
    NormalizeFramerateStage,
    PipelineContext,
    PipelineStage,
    ProbeStage,
    ProgressCallback,
    ReattachAudioStage,
    SetupOutputFolderStage,
    TrimStage,
    VerifySynchronizedFrameCountStage,
    VerifySynchronizedFramerateStage,
)


class SyncPipeline:
    """Shared orchestration for both sync methods (resolves KI-04).

    `SyncPipeline.run` is the single public entry point into `core` -- CLI and
    API callers both go through this rather than duplicating orchestration.
    """

    def __init__(self, stages: list[PipelineStage]) -> None:
        self.stages = stages

    @classmethod
    def for_request(cls, request: SyncRequest) -> "SyncPipeline":
        stages: list[PipelineStage] = [
            SetupOutputFolderStage(),
            DiscoverVideosStage(),
            ProbeStage(),
            NormalizeFramerateStage(),
        ]

        if request.method == SyncMethod.AUDIO:
            stages.append(AudioLagStage())
        else:
            stages.append(BrightnessLagStage())

        stages.append(TrimStage())
        stages.append(VerifySynchronizedFramerateStage())
        stages.append(VerifySynchronizedFrameCountStage())

        if request.method == SyncMethod.AUDIO:
            stages.append(ReattachAudioStage())

        if request.create_debug_artifacts:
            stages.append(DebugArtifactsStage())

        return cls(stages)

    def run(
        self, request: SyncRequest, progress_callback: ProgressCallback | None = None
    ) -> SyncResult:
        start_time = time.time()
        context = PipelineContext(request=request)

        for stage in self.stages:
            context = stage.run(context, progress_callback)

        return SyncResult(
            synchronized_video_folder_path=context.synchronized_folder_path,
            videos_before=context.videos_before,
            videos_after=context.videos,
            lags=context.lags,
            debug_artifact_paths=context.debug_artifact_paths,
            elapsed_seconds=time.time() - start_time,
        )


def run_pipeline(
    request: SyncRequest, progress_callback: ProgressCallback | None = None
) -> SyncResult:
    """Convenience wrapper: build the right stage list for `request` and run it."""
    return SyncPipeline.for_request(request).run(request, progress_callback)
