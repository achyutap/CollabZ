# CollabZ design system

Inter font (next/font), slate-50 background, slate-900 text, indigo-600 primary, soft shadows, rounded-2xl cards. Defined in `src/app/globals.css` (`@layer components`) and `tailwind.config.ts`. Use these classes instead of ad-hoc styles. Live demo: `/dev/components`.

| Class | Recipe |
|---|---|
| `.page` | `max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-6`: wrap every page |
| `.card` | white, `rounded-2xl`, border, `shadow-soft`, padding |
| `.card-hover` | add to `.card` for hover border/shadow (clickable cards) |
| `.section-title` | `text-base font-semibold` heading inside cards |
| `.muted` | `text-sm text-slate-500` |
| `.btn` + `.btn-primary` / `.btn-secondary` / `.btn-danger` / `.btn-ghost` | always combine `.btn` with one variant; add `.btn-sm` for small |
| `.input` | text input / textarea / select; add `!border-red-400` for invalid |
| `.label` | block label above an input |
| `.help` / `.error-text` | helper / validation text below an input |
| `.table-clean` | `<table>`: sticky light header, row hover, `divide-y` (wrap in `overflow-x-auto`) |
| `.badge` | pill with ring; add colour classes, e.g. `bg-emerald-50 text-emerald-700 ring-emerald-200` |
| `.divider` | `border-t border-slate-200` |

Examples
```tsx
<div className="page">
  <PageHeader title="Projects" />
  <div className="card card-hover">...</div>
  <label className="label" htmlFor="x">Name</label>
  <input id="x" className="input" />
  <button className="btn btn-primary btn-sm">Save</button>
</div>
```

Rules: ratings are plain stars (never show "temp"/"final"); lists need loading, empty and error states; layouts must work from 360px.
