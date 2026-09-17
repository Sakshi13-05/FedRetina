/**
 * Mock clinical data for FedRetina.
 *
 * WHAT THIS FILE DOES
 * Provides realistic stand-in data (predictions, grade distribution, weekly trend,
 * hospital node health) so the dashboard renders a believable picture before the
 * real screening pipeline is wired up.
 *
 * INPUT: none. OUTPUT: plain typed objects/arrays consumed by dashboard components.
 */
/** Human-readable severity label for each grade (plain English, no jargon). */
export const GRADE_LABELS = {
    0: "No signs",
    1: "Mild",
    2: "Moderate",
    3: "Severe",
    4: "Advanced",
};
/** Tailwind token class per grade — colour is never the only cue, always paired with text. */
export const GRADE_COLOR_CLASS = {
    0: "text-grade-0",
    1: "text-grade-1",
    2: "text-grade-2",
    3: "text-grade-3",
    4: "text-grade-4",
};
/** CSS variable used by Recharts (which needs a raw colour, not a class). */
export const GRADE_CSS_VAR = {
    0: "var(--success)",
    1: "var(--grade-1)",
    2: "var(--warning)",
    3: "var(--grade-3)",
    4: "var(--danger)",
};
/** Builds an ISO timestamp a given number of hours in the past. */
function hoursAgo(hours) {
    return new Date(Date.now() - hours * 3600_000).toISOString();
}
/** 12 predictions spread over the last week, with 3 flagged for specialist review. */
export const MOCK_PREDICTIONS = [
    { id: "p1", patientId: "PT-2026-0112", grade: 2, confidence: 0.87, uncertaintyScore: 0.042, uncertaintyFlag: false, status: "needs_review", createdAt: hoursAgo(1) },
    { id: "p2", patientId: "PT-2026-0111", grade: 0, confidence: 0.96, uncertaintyScore: 0.011, uncertaintyFlag: false, status: "reviewed", createdAt: hoursAgo(3) },
    { id: "p3", patientId: "PT-2026-0110", grade: 4, confidence: 0.63, uncertaintyScore: 0.081, uncertaintyFlag: true, status: "needs_review", createdAt: hoursAgo(5) },
    { id: "p4", patientId: "PT-2026-0109", grade: 1, confidence: 0.91, uncertaintyScore: 0.02, uncertaintyFlag: false, status: "reviewed", createdAt: hoursAgo(9) },
    { id: "p5", patientId: "PT-2026-0108", grade: 3, confidence: 0.58, uncertaintyScore: 0.093, uncertaintyFlag: true, status: "needs_review", createdAt: hoursAgo(26) },
    { id: "p6", patientId: "PT-2026-0107", grade: 2, confidence: 0.79, uncertaintyScore: 0.048, uncertaintyFlag: false, status: "reviewed", createdAt: hoursAgo(30) },
    { id: "p7", patientId: "PT-2026-0106", grade: 0, confidence: 0.97, uncertaintyScore: 0.008, uncertaintyFlag: false, status: "reviewed", createdAt: hoursAgo(50) },
    { id: "p8", patientId: "PT-2026-0105", grade: 1, confidence: 0.84, uncertaintyScore: 0.031, uncertaintyFlag: false, status: "reviewed", createdAt: hoursAgo(74) },
    { id: "p9", patientId: "PT-2026-0104", grade: 3, confidence: 0.55, uncertaintyScore: 0.102, uncertaintyFlag: true, status: "needs_review", createdAt: hoursAgo(96) },
    { id: "p10", patientId: "PT-2026-0103", grade: 2, confidence: 0.88, uncertaintyScore: 0.039, uncertaintyFlag: false, status: "reviewed", createdAt: hoursAgo(120) },
    { id: "p11", patientId: "PT-2026-0102", grade: 0, confidence: 0.94, uncertaintyScore: 0.014, uncertaintyFlag: false, status: "reviewed", createdAt: hoursAgo(140) },
    { id: "p12", patientId: "PT-2026-0101", grade: 1, confidence: 0.9, uncertaintyScore: 0.022, uncertaintyFlag: false, status: "reviewed", createdAt: hoursAgo(160) },
];
/** Count of predictions per grade, for the donut chart. */
export const GRADE_DISTRIBUTION = [0, 1, 2, 3, 4].map((grade) => ({
    grade,
    label: `Grade ${grade} · ${GRADE_LABELS[grade]}`,
    count: MOCK_PREDICTIONS.filter((p) => p.grade === grade).length,
    color: GRADE_CSS_VAR[grade],
}));
/** Last 7 days of scan volume vs flagged volume, for the trend chart. */
export const WEEKLY_TREND = [
    { day: "Mon", total: 14, flagged: 2 },
    { day: "Tue", total: 18, flagged: 1 },
    { day: "Wed", total: 11, flagged: 3 },
    { day: "Thu", total: 22, flagged: 2 },
    { day: "Fri", total: 26, flagged: 4 },
    { day: "Sat", total: 9, flagged: 1 },
    { day: "Sun", total: 12, flagged: 3 },
];
/** Three partner sites, deliberately mixed state (one offline). */
export const MOCK_NODES = [
    { id: "node-01", name: "City Hospital · Node 01", online: true, lastSync: "4 min ago", datasetSize: 3122 },
    { id: "node-02", name: "Riverside Eye Clinic · Node 02", online: true, lastSync: "11 min ago", datasetSize: 2478 },
    { id: "node-03", name: "Northfield General · Node 03", online: false, lastSync: "2 hours ago", datasetSize: 1904 },
];
/** Headline numbers for the four stat tiles. */
export const DASHBOARD_STATS = {
    scansToday: 12,
    scansYesterday: 9,
    flaggedCases: MOCK_PREDICTIONS.filter((p) => p.uncertaintyFlag).length,
    averageConfidence: Math.round((MOCK_PREDICTIONS.reduce((sum, p) => sum + p.confidence, 0) / MOCK_PREDICTIONS.length) * 100),
    modelStatus: "Active",
    modelUpdated: "Round 34 · 2 hours ago",
};

/** Federated learning rounds, newest first — used by the network monitor. */
export const FL_ROUNDS = [
    { round: 34, finishedAt: "2 hours ago", sitesJoined: 3, accuracy: 0.912, privacyBudget: 1.8, status: "complete" },
    { round: 33, finishedAt: "1 day ago", sitesJoined: 3, accuracy: 0.907, privacyBudget: 2.1, status: "complete" },
    { round: 32, finishedAt: "2 days ago", sitesJoined: 2, accuracy: 0.898, privacyBudget: 2.4, status: "complete" },
    { round: 31, finishedAt: "3 days ago", sitesJoined: 3, accuracy: 0.889, privacyBudget: 2.6, status: "complete" },
    { round: 30, finishedAt: "4 days ago", sitesJoined: 3, accuracy: 0.881, privacyBudget: 2.9, status: "complete" },
];

/** Accuracy per round for the small network chart. */
export const FL_ACCURACY_TREND = [...FL_ROUNDS]
    .reverse()
    .map((r) => ({ day: `R${r.round}`, total: Math.round(r.accuracy * 100), flagged: Math.round(r.privacyBudget * 10) }));

/** Activity trail shown to administrators. */
export const AUDIT_LOG = [
    { id: "a1", who: "asha.menon@city.health", what: "Reviewed scan PT-2026-0112", when: "12 minutes ago" },
    { id: "a2", who: "system", what: "Training round 34 completed across 3 sites", when: "2 hours ago" },
    { id: "a3", who: "daniel.roy@riverside.health", what: "Uploaded 4 scans", when: "3 hours ago" },
    { id: "a4", who: "system", what: "Node 03 went offline", when: "2 days ago" },
    { id: "a5", who: "asha.menon@city.health", what: "Changed site assignment for a colleague", when: "3 days ago" },
];

/** People with access, for the admin screen. */
export const TEAM_MEMBERS = [
    { id: "u1", name: "Asha Menon", email: "asha.menon@city.health", role: "Ophthalmologist", node: "Node 01", admin: true, active: true },
    { id: "u2", name: "Daniel Roy", email: "daniel.roy@riverside.health", role: "Optometrist", node: "Node 02", admin: false, active: true },
    { id: "u3", name: "Priya Nair", email: "priya.nair@northfield.health", role: "Screening technician", node: "Node 03", admin: false, active: false },
];

/** Finds one prediction by its id (used by the detail page). */
export function getPredictionById(id) {
    return MOCK_PREDICTIONS.find((p) => p.id === id) ?? null;
}

/** Per-grade likelihood bars shown on a result, derived from the chosen grade. */
export function gradeProbabilities(grade, confidence) {
    const rest = (1 - confidence) / 4;
    return [0, 1, 2, 3, 4].map((g) => ({
        grade: g,
        label: GRADE_LABELS[g],
        value: g === grade ? confidence : rest,
    }));
}
