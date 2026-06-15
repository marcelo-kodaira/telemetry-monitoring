import { Component, type ReactNode } from "react";

interface State {
  error: Error | null;
}

/** App-level boundary so a render error in one widget shows a message instead of a white screen. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="m-6 rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
          <h2 className="font-semibold">Something went wrong.</h2>
          <p className="mt-1 text-sm">{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
