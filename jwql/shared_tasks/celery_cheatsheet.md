# Cheatsheet on using the JWQL `celery` and `redis` task server

## Introduction

`celery` is a task server infrastructure, which means that, if you have processing work 
that needs to be done, and that you don't want to do in your main process for some reason
(e.g. memory leaks, resource usage, not wanting multiple tasks to run at the same time,
not wanting the same task to be run multiple times at once, etc.) `celery` provides the
ability to

- set up work queues to send tasks to
- assign workers to listen to queues and pick up tasks from them
- co-ordinate between workers as to which worker will handle which task
- keep track of tasks and their status
- pass input data to workers and pass result data back to the calling process
- execute callback functions on the calling processes (if provided)
- schedule tasks for future execution
- revoke tasks that are no longer wanted or needed

In order to co-ordinate between multiple independent workers, celery relies on one of
several services to maintain state. For JWQL, `redis` is used as the task storage and
co-ordination method, and to maintain task status. For the task server to work, you must 
have:

- a single `redis` server, with a known location (server and port). Currently `redis` runs
  on `pljwql2`, and uses port 6379
- one or more `celery` workers, running on one or more servers, and co-ordinating through
  `redis`. Currently JWQL runs only one worker thread on any given server, but runs threads
  on each of `pljwql3`, `pljwql4`, `pljwql5`, and `pljwql6`
- one or more work queues, which the calling processes (monitors) will send to, and which
  the workers (celery) will read from. Currently JWQL uses only a single work queue.
- one or more programs that send tasks to the workers. Currently the JWQL monitors are
  those programs, and they are all run on `pljwql1`

## Celery Command Cheatsheet

- **Starting Celery:**
  - Log in to the server on which you want to start celery, *and* make sure that no `python`
    processes are already running on that server. Currently `pljwql3..6` are reserved for
    `celery` workers.
  - Log in as the appropriate service user
  - Change to the JWQL `shared_tasks` directory (`~/jwql/jwql/jwql/shared_tasks`)
  - Start `celery` in detached mode with `celery -A shared_tasks worker -D -E -ldebug -Ofair -c1 --max-tasks-per-child=1 --prefetch-multiplier 1`
- **Shutting Down Celery Workers:**
  - Log in to any server on which `celery` is running (`pljwql3..6`)
  - Log in as the appropriate service user
  - Change to the JWQL `shared_tasks` directory
  - Run `celery -A shared_tasks control shutdown`
  - Celery worker threads will complete their current task and then exit
- **Killing Celery Workers:**
  - Log in to any server on which `celery` is running (`pljwql3..6`)
  - Log in as the appropriate service user
  - Change to the JWQL `shared_tasks` directory
  - Run `ps auxww | grep 'python' | awk '{print $2}' | xargs kill -9`
  - Celery worker threads will exit immediately, and may not complete their work, update 
    their task status, or release locks
- **Clearing Saved Tasks:**
  - Make sure that no JWQL monitors are running
  - Log in to any server on which `celery` is running (`pljwql3..6`)
  - Log in as the appropriate service user
  - Change to the JWQL `shared_tasks` directory
  - Wait until all `celery` workers have shut down
  - Run `celery -A shared_tasks purge`
  - This will discard any tasks that have not been completed. If a monitor is currently
    running, and is waiting for a task to finish, that task will be purged by this command,
    and the monitor will wait forever for the task to return, so if you didn't make sure 
    that no monitors were running, you will now have to kill any monitor that's currently
    waiting for a task.

## Redis Command Cheatsheet

- **Running Redis:**
  - The JWQL config file has 2 values for redis, `redis_host` and `redis_port`
  - To run `redis`, ssh to the server `redis_host`, and change to the appropriate account
    for that host (ops, test, dev, etc.)
  - `redis_port` tells you which port `redis` should use to listen for connections, and 
    which port `celery` should use to connect to redis. The default value is 6379. If you
    need to run `redis` on a different port, then run `redis-server` with `--port PORT`
  - Run redis with `redis-server --protected-mode no &`. If you will be running jwql
    monitors **and** `celery` on the same server that `redis` is running on, then you can
    omit the `--protected-mode no` argument (having that argument allows redis to accept 
    connections from servers other than `localhost`).
- **Deleting a Redis lock:**
  - *Before you do this, make sure that the process which has the lock has actually crashed or finished without releasing it*
  - Find the name of the lock you need to clear
  - ssh to `redis_host` and change to the appropriate service account
  - run `redis-cli del <NAME>` where `<NAME>` is the name of the lock to be deleted
- **Deleting all Redis file locks:**
  - *Before you do this, make sure that the process which has the lock has actually crashed or finished without releasing it*
  - ssh to `redis_host` and change to the appropriate service account
  - run `redis-cli --scan --pattern 'jw*' | xargs redis-cli del`
- **Stopping Redis:**
  - ssh to `redis_host` and change to the appropriate service account
  - run `ps -e | grep redis` and mark down the process number of `redis-server`
  - run `kill <X>` where `<X>` is the process number from the previous step
  - `redis` will exit gracefully from a `kill` command. Don't use `kill -9` unless a 
    standard `kill` fails to clear the process.

## Using Redis for locking

In addition to acting as a task broker for celery, `redis` also acts as a persistent 
key/value store, which allows it to be used for locking code. Locks should be used to 
protect segments of code which should only be running once, no matter how many processes
want to potentially run them. Using locks *can* be dangerous, and can lead to unpredictable
and difficult-to-find bugs and issues at run-time. As a (very) abbreviated primer to 
locking, you should keep the following principles in mind:

- If you get a lock, be sure to release it, even in the case of errors (i.e. run the locked
  code in a `try/except` block, and put releasing the lock into `finally`)
- If you need multiple locks, **always** acquire and release them in the same order. 
  Otherwise, if you have code that needs both Lock A and Lock B to run, then Process 1 can
  have Lock A (and be waiting for Lock B), and Process 2 can have Lock B (and be waiting 
  for Lock A), and the deadlock will persist forever.
- If you set a lock to automatically time out, make sure that the timeout is long enough
  that by the time it expires, the process that has the lock has either finished or crashed.
  Otherwise you could end up with two processes each thinking they have the lock.
- Before you manually delete a lock to let a process run, make sure that whatever process
  has the lock has either finished with it (and failed to release it) or crashed (and 
  failed to release it).
- Lock as little as you can get away with (but no less)

JWQL has existing ways to lock a single function, or to create a custom lock.

### Locking a single function

To do this, you need to import the `only_one` decorator from `jwql.shared_tasks`, and then
add it as a decorator to to the function to be locked. As an example,

```
from jwql.shared_tasks.shared_tasks import only_one

...
...

@only_one(key='key', timeout=value)
def function(args):
    ...
    ...
```

Note that key strings are global, so if you use the key "my_lock", then only one function
that uses that lock may execute as a time *anywhere*. If you want to lock out a function 
so that only one simultaneous instance of that particular function runs (but you don't 
care about other functions), choose a unique name for the key. If in doubt as to what would
make a unique name, using the module path (e.g. `key=jwql.shared\_tasks.share\_tasks.function`)
will be guaranteed to be unique within the `jwql` module. `timeout` is the number of 
seconds before the lock will be automatically released. If you never want the lock to 
time out, don't provide any value for the `timeout` parameter.

### Using a custom lock

For a worked example of this, look at the `run_pipeline` function in `jwql/shared\_tasks/shared\_tasks.py`.

In order to create a custom lock, you need to import the `REDIS_CLIENT` instance from 
`jwql.shared\_tasks.shared\_tasks`, and then use the `redis` `lock()` and `acquire()` 
functions. As an example,

```
from jwql.shared_tasks.shared_tasks import REDIS_CLIENT

...
...

def some_function(args):
    ...
    ...
    my_lock = REDIS_CLIENT.lock(lock_name, timeout=value)
    have_lock = my_lock.acquire(blocking=True)
    if have_lock:
        try:
            ...
            ...
        finally:
            my_lock.release()
```

In this case, `lock_name` acts the same as `key` above, and `timeout` works in exactly the
same way as it does above. When acquiring the lock, `blocking` describes whether you want 
the code to wait until the lock is available, and then acquire it (`blocking=True`), or 
whether you want the function to return whether or not you have the lock into the `have_lock`
variable (`blocking=False`). In the case where `blocking=False`, if `have_lock=False` then
the lock is already in use, and you must **not** execute any code that requires the lock.
If your code has no way to proceed without the lock, then you should use `blocking=True`.
