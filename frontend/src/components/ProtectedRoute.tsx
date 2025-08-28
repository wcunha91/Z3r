// src/components/ProtectedRoute.tsx
import { useEffect, useState } from "react";
import { me } from "@/services/auth";
import { Navigate, useLocation } from "react-router-dom";

export default function ProtectedRoute({ children }: { children: JSX.Element }) {
  const [status, setStatus] = useState<"checking" | "ok" | "fail">("checking");
  const location = useLocation();

  useEffect(() => {
    (async () => {
      try {
        await me();
        setStatus("ok");
      } catch {
        setStatus("fail");
      }
    })();
  }, []);

  if (status === "checking") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-700 rounded-full animate-spin" />
      </div>
    );
  }

  if (status === "fail") {
    return <Navigate to="/" replace state={{ from: location }} />;
  }

  return children;
}
