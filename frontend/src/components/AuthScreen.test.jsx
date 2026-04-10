import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import AuthScreen from "./AuthScreen";

test("shows register-only fields when auth mode is register", () => {
  render(
    <AuthScreen
      authMode="register"
      credentials={{ username: "", password: "", email: "", display_name: "" }}
      authError=""
      onModeChange={() => {}}
      onCredentialsChange={() => {}}
      onSubmit={(event) => event.preventDefault()}
    />
  );

  expect(screen.getByPlaceholderText("Display name")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
});

test("switches tabs through callback", () => {
  const modes = [];
  render(
    <AuthScreen
      authMode="login"
      credentials={{ username: "", password: "", email: "", display_name: "" }}
      authError=""
      onModeChange={(value) => modes.push(value)}
      onCredentialsChange={() => {}}
      onSubmit={(event) => event.preventDefault()}
    />
  );

  fireEvent.click(screen.getByRole("button", { name: "Register" }));
  expect(modes).toEqual(["register"]);
});
