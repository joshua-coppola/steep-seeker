// Fixed display colors for the 10-band steepness gradient, in ascending
// order. The band boundaries themselves are computed at runtime (see
// steepnessBoundaries) from window.DIFFICULTY_CONSTANTS -- each of the 5
// difficulty colors above is split in two at its midpoint, so this array's
// order must line up with steepnessBoundaries()'s.
const STEEPNESS_COLORS = [
    '#00e600', 'green', '#91a8ee', 'royalblue', '#333333',
    'black', '#ff6666', 'red', '#ffe866', 'gold',
];
const GOLD_STEEPNESS_TOP = 65; // assumed top of gold's open-ended range, just for splitting it in two

// The 9 boundaries between the 10 steepness bands: each of the site's 4
// difficulty thresholds, plus the midpoint of every band they define
// (0-beginner_max, beginner_max-intermediate_max, ..., expert_max-GOLD_STEEPNESS_TOP).
function steepnessBoundaries() {
    const k = window.DIFFICULTY_CONSTANTS;
    return [
        Math.round((0 + k.beginner_max) / 2),
        k.beginner_max,
        Math.round((k.beginner_max + k.intermediate_max) / 2),
        k.intermediate_max,
        Math.round((k.intermediate_max + k.advanced_max) / 2),
        k.advanced_max,
        Math.round((k.advanced_max + k.expert_max) / 2),
        k.expert_max,
        Math.round((k.expert_max + GOLD_STEEPNESS_TOP) / 2),
    ];
}

function buildSteepnessMapping() {
    const boundaries = steepnessBoundaries();
    const mapping = {};
    STEEPNESS_COLORS.forEach((color, i) => {
        const lower = i === 0 ? 0 : boundaries[i - 1];
        const upper = boundaries[i];
        const key = upper === undefined ? `${lower}+` : `${lower}-${upper}`;
        const text = upper === undefined ? `${lower}°+` : `${lower}°-${upper}°`;
        mapping[key] = {text, color};
    });
    return mapping;
}

const colorMappings = {
    get Steepness() {
        return buildSteepnessMapping();
    },
    Difficulty: {
        'green': {
            text: 'Beginner',
            color: 'green'
        },
        'royalblue': {
            text: 'Intermediate',
            color: 'royalblue'
        },
        'black': {
            text: 'Advanced',
            color: 'black'
        },
        'red': {
            text: 'Expert',
            color: 'red'
        },
        'gold': {
            text: 'Extreme',
            color: 'gold'
        },
    }
};
