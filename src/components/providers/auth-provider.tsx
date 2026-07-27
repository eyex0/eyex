import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase/client";

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error?: string; success?: boolean }>;
  signUp: (email: string, password: string, fullName?: string) => Promise<{ error?: string; success?: boolean; needsEmailVerification?: boolean }>;
  signOut: () => Promise<{ error?: string }>;
  resetPassword: (email: string) => Promise<{ error?: string; success?: boolean }>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function buildOrganizationName(authUser: User): string {
  return (
    (authUser.user_metadata?.full_name as string | undefined)?.trim() ||
    (authUser.user_metadata?.company_name as string | undefined)?.trim() ||
    authUser.email?.split("@")[0] ||
    "πX Organization"
  );
}

function buildOrganizationSlug(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 48) || "pix-org"
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  const ensureOrganizationForUser = async (authUser: User | null) => {
    if (!authUser) return;

    try {
      const organizationName = buildOrganizationName(authUser);
      const organizationSlug = buildOrganizationSlug(organizationName);
      await supabase.rpc("ensure_organization", {
        p_slug: organizationSlug,
        p_name: organizationName,
      });
    } catch (error) {
      console.error("Organization provisioning failed:", error);
    }
  };

  useEffect(() => {
    let mounted = true;
    
    const initializeAuth = async () => {
      try {
        const { data: { session: s }, error } = await supabase.auth.getSession();
        if (error) {
          console.error("Auth initialization error:", error);
        }
        if (mounted) {
          setSession(s);
          setUser(s?.user ?? null);
          setLoading(false);
        }
        await ensureOrganizationForUser(s?.user ?? null);
      } catch (error) {
        console.error("Auth initialization failed:", error);
        if (mounted) {
          setLoading(false);
        }
      }
    };

    initializeAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, s) => {
      if (mounted) {
        setSession(s);
        setUser(s?.user ?? null);
        setLoading(false);
      }
      await ensureOrganizationForUser(s?.user ?? null);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const signIn = async (email: string, password: string) => {
    try {
      // Validate inputs
      if (!email || !password) {
        return { error: "Email and password are required" };
      }

      if (!email.includes('@')) {
        return { error: "Please enter a valid email address" };
      }

      if (password.length < 6) {
        return { error: "Password must be at least 6 characters" };
      }

      const { data, error } = await supabase.auth.signInWithPassword({ 
        email: email.toLowerCase().trim(), 
        password 
      });

      if (error) {
        // Handle specific error cases
        if (error.message.includes('Invalid login credentials')) {
          return { error: "Invalid email or password" };
        }
        if (error.message.includes('Email not confirmed')) {
          return { error: "Please verify your email address" };
        }
        return { error: error.message };
      }

      await ensureOrganizationForUser(data.user ?? null);
      return { success: true };
    } catch (error) {
      console.error("Sign in error:", error);
      return { error: "An unexpected error occurred. Please try again." };
    }
  };

  const signUp = async (email: string, password: string, fullName?: string) => {
    try {
      // Validate inputs
      if (!email || !password) {
        return { error: "Email and password are required" };
      }

      if (!email.includes('@') || !email.includes('.')) {
        return { error: "Please enter a valid email address" };
      }

      if (password.length < 8) {
        return { error: "Password must be at least 8 characters" };
      }

      if (!/[A-Z]/.test(password)) {
        return { error: "Password must contain at least one uppercase letter" };
      }

      if (!/[0-9]/.test(password)) {
        return { error: "Password must contain at least one number" };
      }

      const { data, error } = await supabase.auth.signUp({
        email: email.toLowerCase().trim(),
        password,
        options: { 
          data: { 
            full_name: fullName?.trim() || email.split('@')[0]
          },
          emailRedirectTo: `${window.location.origin}/dashboard`
        },
      });

      if (error) {
        if (error.message.includes('User already registered')) {
          return { error: "An account with this email already exists" };
        }
        return { error: error.message };
      }

      await ensureOrganizationForUser(data.session?.user ?? null);

      // Check if email verification is required
      return { 
        success: true, 
        needsEmailVerification: !data.session 
      };
    } catch (error) {
      console.error("Sign up error:", error);
      return { error: "An unexpected error occurred. Please try again." };
    }
  };

  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error("Sign out error:", error);
        return { error: error.message };
      }
      return {};
    } catch (error) {
      console.error("Sign out error:", error);
      return { error: "An unexpected error occurred during sign out" };
    }
  };

  const resetPassword = async (email: string) => {
    try {
      if (!email || !email.includes('@')) {
        return { error: "Please enter a valid email address" };
      }

      const { error } = await supabase.auth.resetPasswordForEmail(email.toLowerCase().trim(), {
        redirectTo: `${window.location.origin}/login`,
      });

      if (error) {
        return { error: error.message };
      }

      return { success: true };
    } catch (error) {
      console.error("Reset password error:", error);
      return { error: "An unexpected error occurred. Please try again." };
    }
  };

  const refreshSession = async () => {
    try {
      const { data: { session: s } } = await supabase.auth.refreshSession();
      setSession(s);
      setUser(s?.user ?? null);
    } catch (error) {
      console.error("Session refresh error:", error);
    }
  };

  return (
    <AuthContext.Provider
      value={{ user, session, loading, signIn, signUp, signOut, resetPassword, refreshSession }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
