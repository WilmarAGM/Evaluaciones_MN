import { createContext, useContext, useState } from "react";
import * as api from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : null;
  });

  async function signIn(email, password) {
    const data = await api.login(email, password);
    localStorage.setItem("token", data.access_token);
    const userInfo = { email: data.email, full_name: data.full_name, role: data.role };
    localStorage.setItem("user", JSON.stringify(userInfo));
    setUser(userInfo);
    return userInfo;
  }

  async function signUp(email, documento, fullName) {
    const data = await api.register(email, documento, fullName);
    localStorage.setItem("token", data.access_token);
    const userInfo = { email: data.email, full_name: data.full_name, role: data.role };
    localStorage.setItem("user", JSON.stringify(userInfo));
    setUser(userInfo);
    return userInfo;
  }

  function signOut() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
