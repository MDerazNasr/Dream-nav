# 0089 Bundled Gaussian Adapter

The remote worker now includes a bundled `gaussian_command_adapter.py` that maps DreamNav's stable worker contract onto a configurable trained Gaussian executable because we need a clean integration point for a real 3DGS engine without baking engine-specific flags into the worker core.
