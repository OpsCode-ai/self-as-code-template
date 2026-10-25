"""Get a cron-made commit onto the remote, without touching work in progress.

Both hourly sweepers (`sweep-telegram-capture.py`, `sweep-private-watch.py`)
commit machine output and then have to push it. Pushing is the whole point:
a commit that only exists on the Pi is not a backup, and it silently diverges
`main` until a human notices, which is how a PR merge ends up blocked by a
capture nobody knew about.

The obvious sequence (`pull --rebase` then `push`) is wrong here, and the
telegram sweeper proved it twice in one log. `git pull --rebase` refuses to
run when ANY file in the tree is unstaged, and that sweeper deliberately
leaves still-being-written captures unstaged so it never commits a half
file. Its own safety feature therefore guaranteed the failure: defer a file,
lose the push, and the commit sits local until some later run happens to
find both new captures and a clean enough tree.

So: push first. In the normal case it is a fast-forward, nothing else is
needed, and no stash ever goes near a file the capture daemon is writing to.
Only when the remote has genuinely moved do we reconcile, and `--autostash`
carries the deferred files through the rebase. Autostash restores by
recorded commit, not by popping the stash stack, which matters because that
stack is shared with every worktree on this machine.
"""
from __future__ import annotations

import subprocess
from typing import Callable, Protocol


class _Run(Protocol):
    def __call__(self, *args: str) -> subprocess.CompletedProcess: ...


def _detail(p: subprocess.CompletedProcess) -> str:
    """Git puts the useful line on either stream depending on the failure."""
    return (p.stderr or "").strip() or (p.stdout or "").strip() or "no output"


def push_with_reconcile(run: _Run) -> tuple[bool, str]:
    """Push HEAD, reconciling with the remote only if the push is rejected.

    `run` is the caller's own git wrapper, already bound to the right repo,
    called as run("push"). It must return a CompletedProcess and must not
    raise on a non-zero exit.

    Returns (ok, message). The message is written for a cron log, so it says
    what happened rather than just that something failed.
    """
    push = run("push")
    if push.returncode == 0:
        return True, "pushed"

    pull = run("pull", "--rebase", "--autostash", "--quiet")
    if pull.returncode != 0:
        # A rebase that stops on a conflict leaves the repo mid-operation, on a
        # detached HEAD with the autostash still held. Leaving it that way would
        # be worse than the bug we are fixing: the next hourly run would find a
        # repo it cannot read, and every guard downstream assumes a settled tree
        # on main. Abort puts it back exactly as we found it, autostash included.
        run("rebase", "--abort")
        return False, (
            "the remote moved and the rebase onto it hit a conflict, so it was "
            "aborted and the commit is held locally for the next run to retry: "
            f"{_detail(pull)}"
        )

    push = run("push")
    if push.returncode != 0:
        return False, (
            "rebased onto the remote but the push still failed, so the commit "
            f"is held locally and the next run will retry: {_detail(push)}"
        )
    return True, "pushed, after rebasing onto a remote that had moved"


def bind(git: Callable[..., subprocess.CompletedProcess], *prefix: object) -> _Run:
    """Adapt a git wrapper that takes leading arguments, e.g. a repo path.

    sweep-private-watch.py's wrapper is git(ops_root, *args), so it binds as
    bind(git, ops_root) and is then callable as run("push") like every other.
    """
    def run(*args: str) -> subprocess.CompletedProcess:
        return git(*prefix, *args)
    return run
