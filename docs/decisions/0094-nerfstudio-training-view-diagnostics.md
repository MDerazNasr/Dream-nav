# 0094 Nerfstudio Training View Diagnostics

DreamNav now includes a repeatable Nerfstudio diagnostics script that renders `gt-rgb` and model `rgb` outputs for training cameras and writes a contact sheet, because reconstruction debugging needs proof of whether the model fit is failing on source views before we keep changing export or viewer code.
