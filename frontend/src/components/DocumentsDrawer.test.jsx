import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DocumentsDrawer from "./DocumentsDrawer";

function buildProps(overrides = {}) {
  return {
    open: true,
    onClose: vi.fn(),
    documents: [
      {
        id: "doc-1",
        name: "Healthcare Notes",
        file_type: "pdf",
        status: "processed",
        chunk_count: 4,
        session_id: "session-1",
        session_title: "Healthcare AI",
      },
      {
        id: "doc-2",
        name: "Market Survey",
        file_type: "txt",
        status: "processed",
        chunk_count: 2,
        session_id: null,
        session_title: null,
      },
    ],
    currentSessionId: "session-1",
    fileInputRef: { current: null },
    uploadingDocument: false,
    docQuestion: "",
    setDocQuestion: vi.fn(),
    docAnswer: null,
    docError: "",
    queryingDocuments: false,
    includeResearch: false,
    setIncludeResearch: vi.fn(),
    documentProgressMessages: [],
    activeDocumentTask: null,
    selectedDocumentIds: [],
    editingDocumentId: null,
    editingDocumentName: "",
    setEditingDocumentName: vi.fn(),
    toggleDocumentSelection: vi.fn(),
    onStartRenameDocument: vi.fn(),
    onSaveDocumentRename: vi.fn(),
    onCancelRenameDocument: vi.fn(),
    onAttachDocument: vi.fn(),
    onDetachDocument: vi.fn(),
    onDeleteDocument: vi.fn(),
    onUpload: vi.fn((event) => event.preventDefault()),
    onAsk: vi.fn((event) => event.preventDefault()),
    onCancelTask: vi.fn(),
    ...overrides,
  };
}

describe("DocumentsDrawer", () => {
  it("filters the library by search and scope", () => {
    render(<DocumentsDrawer {...buildProps()} />);

    expect(screen.getByText("Healthcare Notes")).toBeInTheDocument();
    expect(screen.getByText("Market Survey")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/search by name/i), {
      target: { value: "market" },
    });

    expect(screen.queryByText("Healthcare Notes")).not.toBeInTheDocument();
    expect(screen.getByText("Market Survey")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/search by name/i), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Current session" }));

    expect(screen.getByText("Healthcare Notes")).toBeInTheDocument();
    expect(screen.queryByText("Market Survey")).not.toBeInTheDocument();
  });

  it("shows a confirmation modal before delete", async () => {
    const onDeleteDocument = vi.fn().mockResolvedValue(undefined);
    render(<DocumentsDrawer {...buildProps({ onDeleteDocument })} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/delete healthcare notes/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /delete document/i }));

    expect(onDeleteDocument).toHaveBeenCalledWith("doc-1");
  });
});
