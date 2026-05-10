# 0001 Project Foundation

DreamNav will use an npm workspace monorepo so the browser viewer, shared contracts, and later FastAPI service can evolve independently while keeping the scene data contracts versioned in one repository.

The first implementation slice focuses on shared metadata and API shapes because the PDF makes scene manifests, quality reports, and route contracts the integration boundary between reconstruction, ML, backend serving, and the viewer.
