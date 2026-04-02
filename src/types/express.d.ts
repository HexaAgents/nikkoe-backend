declare namespace Express {
  interface Request {
    user?: {
      id: string;
      email?: string;
      profile: {
        user_id: string;
        name: string;
        email_address: string | null;
        role: string | null;
      } | null;
    };
  }
}
