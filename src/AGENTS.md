# Frontend (Next.js/React)

**Parent:** `./AGENTS.md`

## OVERVIEW

Next.js 14+ app router frontend with React components for wiki visualization, chat interface, and repository browsing.

## STRUCTURE

```
src/
├── app/                    # Next.js app router
│   ├── page.tsx           # Home page
│   ├── wiki/              # Wiki viewer routes
│   │   └── projects/      # Project listing
│   └── api/               # API routes
├── components/            # React components
│   ├── Mermaid.tsx        # Diagram renderer
│   ├── Chat.tsx          # Chat interface
│   └── ...                # UI components
├── hooks/                 # Custom React hooks
├── contexts/              # React contexts
├── types/                 # TypeScript types
├── utils/                 # Utilities
└── messages/              # i18n messages
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Main page | `src/app/page.tsx` |
| Wiki routes | `src/app/wiki/` |
| Components | `src/components/` |
| API routes | `src/app/api/` |

## CONVENTIONS

- ESLint configured (eslint.config.mjs)
- Next.js app router structure
- TypeScript strict mode
- Server components where possible

## COMMANDS

```bash
npm run dev
# Runs on port 3000
```
