import { describe, expect, it } from "vitest";
import { getLensFov } from "./lens";

describe("lens FOV mapping", () => {
  it("maps wider lenses to larger fields of view", () => {
    expect(getLensFov("24mm")).toBeGreaterThan(getLensFov("85mm"));
  });
});
