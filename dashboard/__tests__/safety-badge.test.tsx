import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReviewBadge, SafetyBadge } from "@/components/safety-badge";

describe("SafetyBadge", () => {
  it("shows a clear SFW pass label", () => {
    render(<SafetyBadge status="passed" />);
    expect(screen.getByText(/SFW/)).toBeTruthy();
  });

  it("flags blocked content as danger", () => {
    const { container } = render(<SafetyBadge status="blocked" />);
    expect(container.textContent).toContain("blocked");
  });
});

describe("ReviewBadge", () => {
  it("renders the human review state", () => {
    render(<ReviewBadge status="pending" />);
    expect(screen.getByText(/needs review/)).toBeTruthy();
  });
});
