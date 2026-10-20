export type SignUpValues = { full_name: string; email: string; password: string; confirm_password: string; accepted_terms: boolean };
export type SignInValues = { email: string; password: string; remember: boolean };
export type FieldErrors = Partial<Record<keyof SignUpValues | keyof SignInValues, string>>;
export const emailValid = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
export const passwordRules = (value: string) => [
  {label:'8+ characters', met:value.length >= 8},
  {label:'Upper & lowercase', met:/[A-Z]/.test(value) && /[a-z]/.test(value)},
  {label:'A number', met:/[0-9]/.test(value)},
  {label:'A symbol', met:/[^\w\s]/.test(value)},
];
export function validateSignIn(v: SignInValues): FieldErrors {
  const e: FieldErrors = {};
  if (!v.email.trim()) e.email='Enter your email address.';
  else if (!emailValid(v.email)) e.email='Enter a valid email address.';
  if (!v.password) e.password='Enter your password.';
  else if (v.password.length > 512) e.password='Use no more than 512 characters.';
  return e;
}
export function validateSignUp(v: SignUpValues): FieldErrors {
  const e = validateSignIn({...v, remember:false});
  if (v.full_name.trim().length < 2) e.full_name='Enter your full name (at least 2 characters).';
  else if (v.full_name.trim().length > 100) e.full_name='Use no more than 100 characters.';
  if (v.password && !passwordRules(v.password).every(r=>r.met)) e.password='Meet all four password requirements below.';
  if (!v.confirm_password) e.confirm_password='Confirm your password.';
  else if (v.password !== v.confirm_password) e.confirm_password='Passwords do not match.';
  if (!v.accepted_terms) e.accepted_terms='Accept the Terms of Service and Privacy Policy to continue.';
  return e;
}
