import type { AnyFieldApi } from "@tanstack/react-form";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OtherSpecifyField } from "./other-specify-field";

afterEach(cleanup);

const makeField = (value: string, isBlurred: boolean) =>
  ({
    state: { value, meta: { isBlurred } },
    handleBlur: vi.fn(),
    handleChange: vi.fn(),
  }) as unknown as AnyFieldApi;

describe("OtherSpecifyField", () => {
  it("shows a persistent Required hint while empty and untouched", () => {
    render(<OtherSpecifyField field={makeField("", false)} placeholder="Please specify…" />);
    expect(screen.getByText("Required")).toBeTruthy();
    expect(screen.queryByText("Please specify")).toBeNull();
    expect(screen.getByRole("textbox").getAttribute("aria-invalid")).toBe("false");
  });

  it("shows an error border + message once blurred while empty", () => {
    render(<OtherSpecifyField field={makeField("", true)} placeholder="Please specify…" />);
    expect(screen.getByText("Please specify")).toBeTruthy();
    expect(screen.queryByText("Required")).toBeNull();
    expect(screen.getByRole("textbox").getAttribute("aria-invalid")).toBe("true");
  });

  it("shows no hint or error once filled", () => {
    render(<OtherSpecifyField field={makeField("LangSmith", true)} placeholder="Which other tool(s)?" />);
    expect(screen.queryByText("Required")).toBeNull();
    expect(screen.queryByText("Please specify")).toBeNull();
    expect(screen.getByRole("textbox").getAttribute("aria-invalid")).toBe("false");
  });

  it("propagates change and blur to the field", () => {
    const field = makeField("", false);
    render(<OtherSpecifyField field={field} placeholder="Please specify…" />);
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "x" } });
    fireEvent.blur(input);
    expect(field.handleChange).toHaveBeenCalledWith("x");
    expect(field.handleBlur).toHaveBeenCalled();
  });
});
