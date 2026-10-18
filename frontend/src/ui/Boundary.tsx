// Contains a failed load to the part of the page that needed it, so the rest keeps working.
import { Component, type ReactNode } from "react";

interface BoundaryProps {
  fallback: ReactNode;
  children: ReactNode;
}

export class Boundary extends Component<BoundaryProps, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
