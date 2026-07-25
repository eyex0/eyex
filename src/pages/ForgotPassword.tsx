import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

const forgotSchema = z.object({
  email: z.string().email("Enter a valid email address"),
});

type ForgotForm = z.infer<typeof forgotSchema>;

export default function ForgotPasswordPage() {
  const { resetPassword } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const form = useForm<ForgotForm>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = async (values: ForgotForm) => {
    setSubmitting(true);
    const { error } = await resetPassword(values.email);
    setSubmitting(false);

    if (error) {
      toast.error(error);
      return;
    }

    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
        <div className="w-full max-w-[400px] text-center space-y-6">
          <div className="border border-[#1A1A1C] bg-[#0A0A0C] p-8 space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full border border-[#38BDF8] flex items-center justify-center">
              <svg
                className="h-6 w-6 text-[#38BDF8]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-display font-medium text-[#FAFAFA] tracking-tight">
              Check your email
            </h1>
            <p className="text-sm text-[#A1A1AA] font-light">
              We sent a password reset link to your email address.
            </p>
          </div>
          <Link
            to="/login"
            className="inline-block text-[10px] text-[#38BDF8] hover:text-[#7dd3fc] uppercase tracking-widest font-medium transition-colors"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
      <div className="w-full max-w-[400px] space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-display font-medium text-[#FAFAFA] tracking-tight">
            Reset your password
          </h1>
          <p className="text-sm text-[#A1A1AA] font-light">
            Enter your email and we&apos;ll send you a reset link
          </p>
        </div>

        <div className="border border-[#1A1A1C] bg-[#0A0A0C] p-8">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-[#A1A1AA] text-[10px] uppercase tracking-widest font-medium">
                      Email
                    </FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="email"
                        placeholder="you@yourcorp.com"
                        className="h-11 bg-[#050505] border-[#1A1A1C] text-[#FAFAFA] placeholder:text-[#A1A1AA] focus-visible:ring-[#38BDF8] focus-visible:border-[#38BDF8]"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button
                type="submit"
                disabled={submitting}
                className="w-full h-11 bg-[#FAFAFA] text-[#050505] hover:bg-[#E2E2E2] text-[10px] font-bold uppercase tracking-widest disabled:opacity-50"
              >
                {submitting ? "Sending..." : "Send reset link"}
              </Button>
            </form>
          </Form>
        </div>

        <p className="text-center text-sm text-[#A1A1AA]">
          <Link
            to="/login"
            className="text-[#38BDF8] hover:text-[#7dd3fc] font-medium transition-colors"
          >
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
