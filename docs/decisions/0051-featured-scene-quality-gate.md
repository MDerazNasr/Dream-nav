# 0051 Featured scene quality gate

DreamNav now refuses to feature completed generated scenes when their reconstruction stays too sparse, too unobserved, or too completion-heavy because a technically valid sparse COLMAP export should not replace the stable demo with an obviously unusable 3D scene.

The homepage still prefers the latest generated scene when it clears these thresholds, but otherwise falls back to the locked demo so presentation quality stays predictable.
