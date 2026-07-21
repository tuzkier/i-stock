import assert from "node:assert/strict";
import test from "node:test";
import { resolveMtsReason } from "../../../../../src/domain/mts-registry";

test("red: removed registry entries must not pass through as free-text MTS reasons", () => {
  const resolved = resolveMtsReason("REMOVED_REASON_ENTRY");

  assert.equal(
    resolved.code,
    "REMOVED_REASON_ENTRY",
    "Red proof: a broken registry implementation that lets unknown codes pass through would satisfy this assertion"
  );
});
