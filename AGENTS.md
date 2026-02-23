# Error handling rule (global)
If any command you run returns a non-zero exit code, immediately activate the skill `error-recovery` and follow its loop. You may not declare the task complete until the original failing command reruns successfully and you paste verification evidence.
