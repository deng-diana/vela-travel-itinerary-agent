import { buildPhotoUrl } from '../types'

type VenueCardProps = {
  name: string
  subtitle: string
  photoName?: string | null
  attribution?: string | null
  href?: string | null
  ctaLabel: string
  tags?: string[]
}

export function VenueCard({ name, subtitle, photoName, attribution, href, ctaLabel, tags }: VenueCardProps) {
  const photoUrl = buildPhotoUrl(photoName)

  return (
    <article className="overflow-hidden rounded-[18px] border border-slate-800 bg-slate-950 transition-colors hover:border-slate-700">
      {photoUrl ? (
        <div className="aspect-[16/10] w-full bg-slate-900">
          <img className="h-full w-full object-cover" src={photoUrl} alt={name} loading="lazy" />
        </div>
      ) : null}

      <div className="space-y-2 px-4 py-3">
        <div className="text-sm font-medium text-slate-100">{name}</div>
        <div className="text-xs text-slate-400">{subtitle}</div>
        {tags && tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tags.slice(0, 3).map((tag) => (
              <span key={tag} className="rounded-full border border-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                {tag}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between gap-3">
          {href ? (
            <a
              className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs uppercase tracking-[0.14em] text-slate-200 transition-colors hover:border-slate-600 hover:text-white"
              href={href}
              target="_blank"
              rel="noreferrer"
            >
              {ctaLabel}
            </a>
          ) : null}
          {attribution ? <span className="line-clamp-1 text-[10px] text-slate-500">Photo: {attribution}</span> : null}
        </div>
      </div>
    </article>
  )
}
