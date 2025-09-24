"""
fade_button.py — A QPushButton subclass with a smooth hover fade.

Why this exists
---------------
Qt Style Sheets don’t support CSS transitions, so `:hover` colors snap.
This widget paints its own rounded background and animates the ALPHA of a
chosen hover color (RGB fixed) using QVariantAnimation. That avoids the
“dark flash” you’d get when interpolating from transparent black.

Usage
-----
btn = FadeButton("Complete…", hover_color="#f5dcf4", hover_alpha=90)

Notes
-----
- The text color is pinned for normal/hover/pressed so global QSS rules like
  `QPushButton:pressed { color: white }` won’t flip it on these buttons.
- Background stays transparent in QSS; the tint is painted in paintEvent().
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QPushButton


def _qcolor(c: str | QColor) -> QColor:
    """
    Accept either a QColor or a CSS-like color string (e.g., "#f5dcf4")
    and always return a QColor instance.
    """
    return c if isinstance(c, QColor) else QColor(c)

class FadeButton(QPushButton):
    """
    QPushButton that fades a light hover background.

    Implementation details:
    - RGB is kept fixed to `hover_color`; only ALPHA is animated.
      This prevents the initial darkening you’d see if fading from black.
    - The rounded background is drawn in paintEvent(), not via QSS, so
      global `QPushButton:hover` rules can’t override/snap the color.
    - Text color is fixed across states so it won’t flip on press.
    """

    def __init__(
        self,
        text: str = "",
        *,
        hover_color: str | QColor = "#f5dcf4",
        hover_alpha: int = 90,
        duration_ms: int = 200,
        radius_px: int = 10,
        parent=None,
    ) -> None:
        super().__init__(text, parent)

        # Prepare base (alpha=0) and hover (alpha=hover_alpha) colors.
        base = _qcolor(hover_color)
        base.setAlpha(0)           # pink at 0% opacity
        hover = _qcolor(hover_color)
        hover.setAlpha(hover_alpha)

        # Store current fill state and geometry.
        self._base = base
        self._hover = hover
        self._current = QColor(base)
        self._radius = radius_px

        # Ensure we receive hover events and can paint our own background.
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Keep the widget's own background transparent; we paint the tint.
        # (This gets overwritten below by _set_text_color but is kept here
        # for clarity; both styles specify transparent bg + radius.)
        self.setStyleSheet(
            f"QPushButton {{ background-color: transparent; border-radius: {radius_px}px; }}"
            )

        # Animate color values smoothly in/out on hover.
        self._anim = QVariantAnimation(
            self, duration=duration_ms, easingCurve=QEasingCurve.InOutCubic
            )
        self._anim.valueChanged.connect(self._on_anim_value)

        # Pin text color for normal/hover/pressed so it doesn't flip to white.
        self._set_text_color("#000000")

    def _set_text_color(self, css_color: str) -> None:
        """
        Force a specific text color for this button instance across states.
        This overrides any global QSS like QPushButton:pressed { color: white }.
        """
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                border-radius: {self._radius}px;
                color: {css_color};
            }}
            QPushButton:hover  {{ color: {css_color}; }}
            QPushButton:pressed{{ color: {css_color}; }}
            """
        )

    # ------- Animation sinks & event handlers -------

    def _on_anim_value(self, color: QColor) -> None:
        """Update the current fill color as the animation progresses."""
        self._current = color
        self.update()

    def enterEvent(self, e):
        """Start fading to the hover color (alpha up) on mouse enter."""
        self._anim.stop()
        self._anim.setStartValue(self._current)
        self._anim.setEndValue(self._hover)     # fade to pink@hover_alpha
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        """Fade back to transparent (alpha down) on mouse leave."""
        self._anim.stop()
        self._anim.setStartValue(self._current)
        self._anim.setEndValue(self._base)      # fade back to pink@0
        self._anim.start()
        super().leaveEvent(e)

    # ------- Painting -------

    def paintEvent(self, e):
        """
        Paint a rounded rect background with the current animated color,
        then let QPushButton draw its text/focus/etc. on top.
        """
        if self._current.alpha() > 0:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setPen(Qt.NoPen)
            p.setBrush(self._current)
            # Slightly shrink rect on the right/bottom so the arc looks crisp.
            r = self.rect().adjusted(0, 0, -1, -1)
            p.drawRoundedRect(r, self._radius, self._radius)

        super().paintEvent(e)
