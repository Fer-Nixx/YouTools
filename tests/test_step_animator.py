"""Tests para StepAnimator: el driver que reemplaza el loop de animación
duplicado en motion.py/buttons.py/hub_view.py (candidato 1 del reporte de
arquitectura).

Seam bajo prueba: `StepAnimator.run(steps, duration_ms, on_step, on_done)`.
Se prueba contra un doble de widget en memoria -- sin Tk, sin display --
porque lo único que StepAnimator necesita de un widget real es
`after`/`after_cancel`/`winfo_exists`. Las curvas de easing (`ease_out`,
`spring_ease`) y el color (`lerp_color`) no se tocan en este módulo: eso
sigue siendo responsabilidad exclusiva de cada llamador.
"""

import unittest

from src.components.motion import StepAnimator


class FakeWidget:
    """Doble de un widget de Tkinter: implementa solo lo que StepAnimator
    necesita, sin mainloop real. `fire_next()` simula que Tk despachó el
    próximo callback programado con `.after()`."""

    def __init__(self, exists: bool = True):
        self.exists = exists
        self.scheduled = []  # [(job_id, delay, callback, args)]
        self.cancelled_ids = []
        self._next_id = 0

    def after(self, delay, callback, *args):
        self._next_id += 1
        job_id = self._next_id
        self.scheduled.append((job_id, delay, callback, args))
        return job_id

    def after_cancel(self, job_id):
        self.cancelled_ids.append(job_id)

    def winfo_exists(self):
        return self.exists

    def fire_next(self):
        job_id, _delay, callback, args = self.scheduled.pop(0)
        callback(*args)


class StepAnimatorRunTests(unittest.TestCase):
    def test_calls_on_step_for_every_step_including_the_last(self):
        widget = FakeWidget()
        seen = []

        StepAnimator(widget).run(steps=3, duration_ms=90, on_step=seen.append)
        while widget.scheduled:
            widget.fire_next()

        self.assertEqual(seen, [0, 1, 2, 3])

    def test_delay_between_steps_matches_duration_over_steps(self):
        widget = FakeWidget()

        StepAnimator(widget).run(steps=8, duration_ms=150, on_step=lambda i: None)

        self.assertTrue(widget.scheduled)
        _, delay, _, _ = widget.scheduled[0]
        self.assertEqual(delay, 150 // 8)

    def test_delay_never_drops_below_one_millisecond(self):
        widget = FakeWidget()

        StepAnimator(widget).run(steps=20, duration_ms=5, on_step=lambda i: None)

        _, delay, _, _ = widget.scheduled[0]
        self.assertEqual(delay, 1)

    def test_on_done_runs_once_after_the_last_step(self):
        widget = FakeWidget()
        done_calls = []

        StepAnimator(widget).run(
            steps=2, duration_ms=20, on_step=lambda i: None,
            on_done=lambda: done_calls.append(True),
        )
        while widget.scheduled:
            widget.fire_next()

        self.assertEqual(done_calls, [True])

    def test_on_done_is_optional(self):
        widget = FakeWidget()

        StepAnimator(widget).run(steps=2, duration_ms=20, on_step=lambda i: None)
        while widget.scheduled:
            widget.fire_next()  # no debe reventar sin on_done

    def test_stops_calling_on_step_once_the_widget_is_destroyed(self):
        widget = FakeWidget()
        seen = []

        StepAnimator(widget).run(steps=5, duration_ms=50, on_step=seen.append)
        widget.fire_next()  # step 1
        widget.exists = False
        widget.fire_next()  # el driver debe frenar acá, no llegar a step 2

        self.assertEqual(seen, [0, 1])

    def test_does_not_call_on_done_if_the_widget_was_destroyed_mid_animation(self):
        widget = FakeWidget()
        done_calls = []

        StepAnimator(widget).run(
            steps=2, duration_ms=20, on_step=lambda i: None,
            on_done=lambda: done_calls.append(True),
        )
        widget.exists = False
        while widget.scheduled:
            widget.fire_next()

        self.assertEqual(done_calls, [])

    def test_a_new_run_cancels_the_previous_pending_job(self):
        widget = FakeWidget()
        animator = StepAnimator(widget)

        animator.run(steps=8, duration_ms=150, on_step=lambda i: None)
        pending_job_id = widget.scheduled[0][0]

        animator.run(steps=8, duration_ms=150, on_step=lambda i: None)

        self.assertIn(pending_job_id, widget.cancelled_ids)


if __name__ == "__main__":
    unittest.main()
