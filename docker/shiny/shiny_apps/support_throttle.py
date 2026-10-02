import functools
import time
from shiny import reactive

def throttle(delay_secs: float):
    def wrapper(f):
        trigger = reactive.Value(0)
        last_triggered = reactive.Value(None)
        last_signaled = reactive.Value(0.0)
        cached = reactive.calc(f)

        @reactive.effect
        def timer():
            # Trigger dependency track
            trigger()
            
            if last_triggered.get() is not None and last_signaled.get() < last_triggered.get():
                return

            now = time.time()
            if last_triggered.get() is None or (now - last_triggered.get()) >= delay_secs:
                last_triggered.set(now)
                with reactive.isolate():
                    trigger.set(trigger() + 1)
            else:
                reactive.invalidate_later(delay_secs - (now - last_triggered.get()))

        @reactive.calc
        @reactive.event(trigger, ignore_none=False)
        @functools.wraps(f)
        def throttled():
            last_signaled.set(time.time())
            return cached()

        return throttled
    return wrapper
