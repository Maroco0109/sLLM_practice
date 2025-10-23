import { render, screen } from "@testing-library/react";
import HomePage from "../app/page";

describe("HomePage", () => {
  it("renders title and copy", () => {
    render(<HomePage />);
    expect(
      screen.getByRole("heading", { name: /sLLM-KR Chatbot/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Placeholder Next\.js entry point/i)
    ).toBeInTheDocument();
  });
});

