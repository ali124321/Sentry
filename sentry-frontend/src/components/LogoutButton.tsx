"use client";

import { useRouter } from "next/navigation";

export default function Logout() {
  const router = useRouter();

  const logout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  return <button onClick={logout}>Logout</button>;
}
