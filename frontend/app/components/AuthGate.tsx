"use client";

import { useAuth } from "../lib/useAuth";

type AuthGateProps = {
  children: React.ReactNode;
};

export default function AuthGate({ children }: AuthGateProps) {
  useAuth();
  return <>{children}</>;
}
