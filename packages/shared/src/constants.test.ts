import { describe, expect, it } from "vitest";
import { SCENE_SCHEMA_VERSION } from "./constants.js";

describe("shared constants", () => {
  it("publishes a version for manifest compatibility checks", () => {
    expect(SCENE_SCHEMA_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
  });
});
