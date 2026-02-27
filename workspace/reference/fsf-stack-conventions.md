# FSF Stack Conventions

## Core Stack
Vite + TypeScript + React + shadcn-ui + Tailwind + Supabase + React Query + Vitest + Resend

## Banned Technologies
NEVER use: Next.js, Jest, Airtable, Redux, CSS Modules, Express, Firebase, Prisma

## Tool Preferences
- Scheduling: GHL (not Calendly)
- Outreach automation: HeyReach (not Phantombuster)
- Screen recording: CleanShot (not Loom)
- Email sending: Resend (not Mailchimp)
- Email domains: hello@learnwell.com or outreach@learnwell.com only
- GHL personalization tags: {{contact.first_name}}

## Component Patterns
- UI components: shadcn-ui (not MUI, not Chakra)
- Styling: Tailwind utility classes (no CSS modules, no styled-components)
- State: React Query for server state, React context for local state (no Redux)
- Forms: React Hook Form + Zod validation
- Testing: Vitest + React Testing Library (not Jest)

## Database
- Supabase (Postgres) with Row Level Security (RLS) on all tables
- TypeScript types generated from database schema
- Real-time subscriptions where appropriate

## Project Structure
```
src/
├── components/    # Reusable UI components
├── features/      # Feature-specific components and logic
├── hooks/         # Custom React hooks
├── lib/           # Utilities, Supabase client, helpers
├── pages/         # Route-level components
└── types/         # Shared TypeScript types
```
