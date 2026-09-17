/**
 * Public landing page for FedRetina.
 */
import { createFileRoute, Link } from "@tanstack/react-router";
import { ShieldCheck, Network, Eye, FileText } from "lucide-react";
import { Logo } from "@/components/fedretina/Logo";
import { AmbientShapes } from "@/components/fedretina/motion/AmbientShapes";
import { Reveal } from "@/components/fedretina/motion/Reveal";
import { RotatingQuote } from "@/components/fedretina/motion/RotatingQuote";
import { CountUp } from "@/components/fedretina/motion/CountUp";
import { LivePulse } from "@/components/fedretina/motion/LivePulse";

const FEATURES = [
  {
    icon: Eye,
    title: "Grades in seconds",
    body: "Upload a retina photo and get a severity grade with a plain-English explanation.",
  },
  {
    icon: ShieldCheck,
    title: "Images stay put",
    body: "Patient photos never leave your hospital — only anonymous learning is shared.",
  },
  {
    icon: Network,
    title: "Learns across sites",
    body: "Every participating clinic improves the shared model without sharing records.",
  },
  {
    icon: FileText,
    title: "Reports ready to file",
    body: "Each result comes with a clear summary you can save to the patient record.",
  },
];

const SITES = [
  "St. Mary's Eye Unit",
  "Northside Diabetes Centre",
  "Riverbank General",
  "Lakeview Screening",
  "Central Teaching Hospital",
  "Harbour Clinic",
];

const NOTES = [
  { text: "We see the urgent cases first now, instead of at the end of the list.", source: "Screening lead, Riverbank General" },
  { text: "Nothing leaves our building, so approval took days rather than months.", source: "Data officer, Harbour Clinic" },
  { text: "The plain summary means I can explain the result to the patient there and then.", source: "Optometrist, Lakeview" },
];

const STATS = [
  { value: 1240, suffix: "", label: "Scans reviewed this week" },
  { value: 12, suffix: "", label: "Hospitals sharing learning" },
  { value: 94, suffix: "%", label: "Average confidence" },
];

function Landing() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-background">
      <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <Link
          to="/auth"
          className="inline-flex min-h-11 items-center rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary-hover hover:shadow-md"
        >
          Sign in
        </Link>
      </header>

      <main>
        {/* Hero */}
        <section className="relative isolate mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
          <AmbientShapes dense />
          <span className="fr-rise inline-flex items-center gap-2 rounded-full bg-primary-light px-3 py-1 text-xs font-semibold text-primary">
            <LivePulse label="Privacy-first screening" tone="primary" />
          </span>
          <h1 className="fr-rise mt-5 text-4xl font-bold tracking-tight text-foreground sm:text-5xl" style={{ animationDelay: "80ms" }}>
            Spot diabetic eye disease earlier, without moving patient data
          </h1>
          <p className="fr-rise mx-auto mt-5 max-w-2xl text-lg text-secondary-text" style={{ animationDelay: "160ms" }}>
            FedRetina reviews retina photos at the bedside and flags the cases that need a specialist
            today — while every image stays inside your own hospital.
          </p>
          <div className="fr-rise mt-8 flex flex-wrap justify-center gap-3" style={{ animationDelay: "240ms" }}>
            <Link
              to="/auth"
              className="inline-flex min-h-12 items-center rounded-md bg-primary px-6 text-sm font-semibold text-primary-foreground transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary-hover hover:shadow-lg"
            >
              Get started
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex min-h-12 items-center rounded-md border border-border bg-surface px-6 text-sm font-semibold text-secondary-text transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary-light hover:text-primary"
            >
              View dashboard
            </Link>
          </div>

          {/* Animated scanning eye */}
          <div className="fr-rise relative mx-auto mt-14 flex size-44 items-center justify-center" style={{ animationDelay: "320ms" }} aria-hidden>
            <span className="fr-ring absolute size-32 rounded-full border-2 border-primary" />
            <span className="fr-ring absolute size-32 rounded-full border-2 border-primary" style={{ animationDelay: "1.2s" }} />
            <span className="relative flex size-32 items-center justify-center overflow-hidden rounded-full border border-border bg-surface shadow-md">
              <Eye size={44} className="text-primary" />
              <span className="fr-scanline absolute inset-x-0 h-6 bg-primary/25 blur-[2px]" />
            </span>
          </div>
        </section>

        {/* Ticker */}
        <section className="relative overflow-hidden border-y border-border bg-surface-2 py-3" aria-hidden>
          <div className="fr-marquee flex w-max gap-10 whitespace-nowrap text-sm font-medium text-muted-foreground">
            {[...SITES, ...SITES].map((site, i) => (
              <span key={`${site}-${i}`} className="flex items-center gap-2">
                <span className="size-1.5 rounded-full bg-primary" />
                {site}
              </span>
            ))}
          </div>
        </section>

        {/* Counters */}
        <section className="mx-auto grid max-w-4xl gap-4 px-4 py-14 sm:grid-cols-3 sm:px-6">
          {STATS.map((stat, i) => (
            <Reveal key={stat.label} delay={i * 120}>
              <div className="fr-lift rounded-lg border border-border bg-surface p-6 text-center shadow-sm">
                <p className="text-3xl font-bold tracking-tight text-primary">
                  <CountUp value={stat.value} suffix={stat.suffix} />
                </p>
                <p className="mt-1 text-sm text-muted-foreground">{stat.label}</p>
              </div>
            </Reveal>
          ))}
        </section>

        {/* Features */}
        <section className="relative isolate mx-auto max-w-6xl px-4 pb-16 sm:px-6">
          <AmbientShapes />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map(({ icon: Icon, title, body }, i) => (
              <Reveal key={title} delay={i * 110} as="article">
                <article className="fr-lift group h-full rounded-lg border border-border bg-surface p-6 shadow-sm">
                  <span className="inline-flex size-10 items-center justify-center rounded-md bg-primary-light text-primary transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3">
                    <Icon size={20} aria-hidden />
                  </span>
                  <h2 className="mt-4 text-base font-semibold text-foreground">{title}</h2>
                  <p className="mt-2 text-sm text-muted-foreground">{body}</p>
                </article>
              </Reveal>
            ))}
          </div>
        </section>

        {/* Quotes */}
        <section className="mx-auto max-w-2xl px-4 pb-24 sm:px-6">
          <Reveal>
            <RotatingQuote items={NOTES} />
          </Reveal>
        </section>
      </main>

      <footer className="border-t border-border py-8 text-center text-sm text-muted-foreground">
        FedRetina — a screening aid. Clinical decisions always rest with the care team.
      </footer>
    </div>
  );
}

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "FedRetina — Private retina screening for diabetes care" },
      {
        name: "description",
        content: "FedRetina helps eye teams grade diabetic retina scans in seconds, with patient images never leaving the hospital.",
      },
      { property: "og:title", content: "FedRetina — Private retina screening for diabetes care" },
      {
        property: "og:description",
        content: "Grade diabetic retina scans in seconds, with patient images never leaving the hospital.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Landing,
});