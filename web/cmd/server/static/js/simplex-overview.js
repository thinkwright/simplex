// Simplex Overview - Vanilla JS Implementation
// No frameworks, no build step, just clean JavaScript

const EPISODES = [
  {
    id: 0,
    label: "INTRO",
    title: "Simplex",
    subtitle: "A Specification Format for AI Agents",
    content: null,
    type: "hero",
  },
  {
    id: 1,
    label: "WHAT",
    title: "What Is It?",
    subtitle: "The basics",
    content: [
      "Simplex is a specification format for describing work that autonomous agents will perform. It captures what needs to be done and how to know when it's done, without prescribing how to do it.",
      "It is not a programming language and does not require a formal grammar or parser for agent interpretation. Agents read specifications as semi-structured text and extract meaning directly; tooling may use tolerant parsers to inspect that structure.",
      "Instead of grammar rules, Simplex uses landmarks — structural markers like FUNCTION, RULES, DONE_WHEN, and EXAMPLES that LLMs recognize and orient around. Content under a landmark continues until the next landmark or end of document.",
      "Natural language is how most people communicate intent to agents, but it can be extremely ambiguous and inconsistent from person to person. Simplex provides a structured way for software architects to express what they want built — clearly enough that agents can act on it without interactive clarification.",
      "When agents work autonomously for extended periods, this reliability matters. Simplex occupies the middle ground between natural language (too ambiguous) and programming languages (too prescriptive).",
      "Although Simplex tolerates formatting inconsistencies and notational looseness, the bundled linter currently performs deterministic structural and heuristic checks. Semantic validity remains a broader review requirement.",
    ],
    type: "text",
  },
  {
    id: 2,
    label: "USE",
    title: "What's It For?",
    subtitle: "Use cases",
    content: [
      {
        icon: "◷",
        heading: "Long Horizon Autonomous Coding",
        text: "Agents working autonomously for extended periods need instructions that stand alone. Simplex specs serve as complete contracts — no interactive clarification, no ambiguity, no back-and-forth.",
      },
      {
        icon: "△",
        heading: "Greenfield Rapid Prototyping",
        text: "Starting from scratch with a clear idea of what you want built. Write a Simplex spec that describes the behavior, hand it to an agent, and let it make the implementation choices.",
      },
      {
        icon: "⬡",
        heading: "Brownfield Feature Development",
        text: "Adding capabilities to existing systems. Simplex specs describe the new behavior and constraints without dictating how it integrates — the agent works within whatever codebase it finds.",
      },
    ],
    type: "cards",
  },
  {
    id: 3,
    label: "HOW",
    title: "How It Works",
    subtitle: "Landmarks, not grammar",
    content: {
      lines: [
        { type: "keyword", text: "FUNCTION: ", value: "filter_policies(policies, ids, tags) → filtered list" },
        { type: "blank" },
        { type: "keyword", text: "RULES:", value: "" },
        { type: "rule", text: '  - if neither ids nor tags provided, return all' },
        { type: "rule", text: '  - if only ids provided, match those IDs' },
        { type: "rule", text: '  - if both provided, return union, deduplicated' },
        { type: "blank" },
        { type: "keyword", text: "DONE_WHEN:", value: "" },
        { type: "rule", text: '  - returned list matches criteria exactly' },
        { type: "rule", text: '  - no duplicates in returned list' },
        { type: "blank" },
        { type: "keyword", text: "EXAMPLES:", value: "" },
        { type: "example", text: '  ([p1,p2,p3], none, none) → [p1,p2,p3]' },
        { type: "example", text: '  ([p1,p2,p3], [p1.id], none) → [p1]' },
      ],
      note: "No formal grammar is required for agent interpretation. Tooling uses a tolerant landmark parser. Syntax is forgiving — meaning must be precise. The linter checks structure and uses a count-based branch/example heuristic; semantic coverage still requires review.",
    },
    type: "code",
  },
  {
    id: 4,
    label: "PILLARS",
    title: "Five Pillars",
    subtitle: "Design principles",
    content: [
      { num: "01", name: "Enforced Simplicity", desc: "If it can't be expressed simply, decompose it. Complexity that cannot be decomposed is complexity that is not yet understood. The linter flags overly complex constructs and rejects them." },
      { num: "02", name: "Syntactic Tolerance", desc: "Typos and formatting quirks are fine. Vague meaning is not. Sloppy notation is acceptable; ambiguous intent is invalid." },
      { num: "03", name: "Testability", desc: "Every function requires examples — not illustrations, but contracts. Work isn't done until output matches them." },
      { num: "04", name: "Completeness", desc: "A valid spec must stand alone. No back-and-forth. No 'what did you mean by X?' The spec is the whole story." },
      { num: "05", name: "Implementation Autonomy", desc: "Describe behavior, never implementation. Algorithms, data structures, and tech choices belong to the agent." },
    ],
    type: "pillars",
  },
  {
    id: 5,
    label: "LANDMARKS",
    title: "The Landmarks",
    subtitle: "What goes in a spec",
    content: {
      intro: "Simplex defines thirteen landmarks. Five are required for a valid spec. The rest add precision when needed.",
      required: [
        { kw: "FUNCTION", desc: "Names the operation, its inputs, and return type" },
        { kw: "RULES", desc: "Behavioral spec — describes outcomes, not steps" },
        { kw: "DONE_WHEN", desc: "Observable criteria for when work is complete" },
        { kw: "EXAMPLES", desc: "Concrete input/output pairs that serve as contracts" },
        { kw: "ERRORS", desc: "Maps failure conditions to responses" },
      ],
      optional: [
        { kw: "DATA", desc: "Defines the shape of a type — fields, constraints" },
        { kw: "CONSTRAINT", desc: "Invariants that hold across all functions" },
        { kw: "READS / WRITES", desc: "Shared memory dependencies between agents" },
        { kw: "TRIGGERS", desc: "Conditions for when an agent picks up work" },
        { kw: "NOT_ALLOWED", desc: "Boundaries on what a function must not do" },
        { kw: "HANDOFF", desc: "What passes to the next stage on success or failure" },
        { kw: "UNCERTAIN", desc: "When to signal low confidence instead of proceeding" },
      ],
      footnote: "Agents ignore unrecognized landmarks rather than rejecting the document; the current linter reports them as warnings.",
    },
    type: "landmarks",
  },
  {
    id: 6,
    label: "BUILD",
    title: "The Planner",
    subtitle: "Start writing specs now",
    content: {
      intro: "Simplex specifications are written by hand. The process of writing is part of the point; you can't specify what you haven't thought through.",
      philosophy: "The Planner is a companion tool for learning the format. It lets you explore how the landmarks fit together and see what a valid spec looks like before you start writing your own.",
      steps: [
        { icon: "→", text: "See how FUNCTION, RULES, DONE_WHEN, and EXAMPLES relate to each other" },
        { icon: "→", text: "Try expressing an idea and observe the structure it produces" },
        { icon: "→", text: "Understand why each landmark exists and when it's required" },
        { icon: "→", text: "Get familiar enough that the format doesn't slow you down when writing" },
      ],
      cta: {
        text: "Open the Planner",
        url: "https://simplex-spec.org/planner",
      },
      closing: "Once the patterns feel natural, you won't need it. Writing Simplex specs promotes clear thinking.",
    },
    type: "planner",
  },
];

// State
let state = {
  current: 0,
  transitioning: false,
  direction: 1,
};

// Animation utilities
function typeWriter(element, text, speed = 18, delay = 0, onComplete) {
  let i = 0;
  const cursor = document.createElement('span');
  cursor.style.opacity = '0';
  cursor.style.transition = 'opacity 0.1s';
  cursor.textContent = '▊';
  element.appendChild(cursor);

  setTimeout(() => {
    cursor.style.opacity = '1';
    const interval = setInterval(() => {
      if (i < text.length) {
        element.textContent = text.slice(0, i + 1);
        element.appendChild(cursor);
        i++;
      } else {
        cursor.style.opacity = '0';
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    }, speed);
  }, delay);
}

function fadeIn(element, delay = 0, duration = 600) {
  element.style.opacity = '0';
  element.style.transform = 'translateY(18px)';
  element.style.transition = `opacity ${duration}ms cubic-bezier(0.25,0.46,0.45,0.94), transform ${duration}ms cubic-bezier(0.25,0.46,0.45,0.94)`;

  setTimeout(() => {
    element.style.opacity = '1';
    element.style.transform = 'translateY(0)';
  }, delay);
}

function staggerIn(elements, baseDelay = 0, stagger = 120) {
  elements.forEach((el, i) => {
    fadeIn(el, baseDelay + i * stagger);
  });
}

// Episode renderers
function renderHero() {
  const container = document.createElement('div');
  container.style.cssText = 'display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100%;text-align:center;padding:40px 24px';

  const label = document.createElement('div');
  label.style.cssText = "font-size:11px;letter-spacing:6px;text-transform:uppercase;padding-left:6px;color:#8af;font-family:'JetBrains Mono',monospace;margin-bottom:24px;opacity:0;transition:opacity 0.8s";
  label.textContent = 'specification format';
  container.appendChild(label);

  const title = document.createElement('h1');
  title.style.cssText = "font-size:clamp(52px,10vw,88px);font-weight:700;letter-spacing:-2px;font-family:'Inter',sans-serif;color:#f0f0f0;line-height:1;margin-bottom:20px;opacity:0;transform:scale(0.92);transition:all 1s cubic-bezier(0.25,0.46,0.45,0.94)";
  title.textContent = 'Simplex';
  container.appendChild(title);

  const subtitle = document.createElement('p');
  subtitle.style.cssText = "font-size:clamp(16px,2.5vw,22px);color:#999;font-weight:300;font-family:'Inter',sans-serif;max-width:520px;line-height:1.6;opacity:0;transform:translateY(12px);transition:all 0.8s cubic-bezier(0.25,0.46,0.45,0.94)";
  subtitle.textContent = 'A high fidelity input for autonomous agents';
  container.appendChild(subtitle);

  const link = document.createElement('a');
  link.href = 'https://simplex-spec.org';
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.style.cssText = "font-size:14px;color:#8af;font-weight:400;font-family:'JetBrains Mono',monospace;text-decoration:none;margin-top:20px;opacity:0;transition:opacity 1s";
  link.textContent = 'simplex-spec.org';
  container.appendChild(link);

  const credit = document.createElement('div');
  credit.style.cssText = "font-size:12px;color:#555;font-family:'Inter',sans-serif;margin-top:16px;opacity:0;transition:opacity 1s";
  credit.textContent = 'Brandon Huey, January 2026';
  container.appendChild(credit);

  const nav = document.createElement('div');
  nav.style.cssText = "margin-top:36px;font-size:13px;color:#555;font-family:'Inter',sans-serif;opacity:0;transition:opacity 1s;animation:pulse 2s infinite";
  nav.textContent = '→ navigate pages';
  container.appendChild(nav);

  setTimeout(() => label.style.opacity = '1', 400);
  setTimeout(() => {
    title.style.opacity = '1';
    title.style.transform = 'scale(1)';
  }, 400);
  setTimeout(() => {
    subtitle.style.opacity = '1';
    subtitle.style.transform = 'translateY(0)';
  }, 1200);
  setTimeout(() => {
    link.style.opacity = '1';
    credit.style.opacity = '1';
    nav.style.opacity = '1';
  }, 2000);

  return container;
}

function renderText(episode) {
  const container = document.createElement('div');
  container.style.cssText = 'padding:40px 24px;max-width:600px;margin:0 auto';

  const header = renderEpisodeHeader(episode);
  container.appendChild(header);

  const content = document.createElement('div');
  content.style.cssText = 'display:flex;flex-direction:column;gap:20px';

  episode.content.forEach((para, i) => {
    const p = document.createElement('p');
    p.style.cssText = `font-size:clamp(15px,2vw,17px);color:${i === 0 ? '#8af' : '#aaa'};line-height:1.75;font-family:'Inter',sans-serif;font-weight:${i === 0 ? 400 : 300}`;
    p.textContent = para;
    content.appendChild(p);
  });

  container.appendChild(content);
  staggerIn(Array.from(content.children), 400, 300);

  return container;
}

function renderCards(episode) {
  const container = document.createElement('div');
  container.style.cssText = 'padding:40px 24px;max-width:640px;margin:0 auto';

  const header = renderEpisodeHeader(episode);
  container.appendChild(header);

  const cardsContainer = document.createElement('div');
  cardsContainer.style.cssText = 'display:flex;flex-direction:column;gap:16px';

  episode.content.forEach(card => {
    const cardEl = document.createElement('div');
    cardEl.style.cssText = 'background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:24px 28px;backdrop-filter:blur(8px)';

    const icon = document.createElement('div');
    icon.style.cssText = 'font-size:28px;margin-bottom:8px';
    icon.textContent = card.icon;
    cardEl.appendChild(icon);

    const heading = document.createElement('div');
    heading.style.cssText = "font-size:14px;font-weight:600;color:#8af;letter-spacing:0.5px;font-family:'JetBrains Mono',monospace;margin-bottom:8px";
    heading.textContent = card.heading;
    cardEl.appendChild(heading);

    const text = document.createElement('div');
    text.style.cssText = "font-size:15px;color:#aaa;line-height:1.65;font-family:'Inter',sans-serif";
    text.textContent = card.text;
    cardEl.appendChild(text);

    cardsContainer.appendChild(cardEl);
  });

  container.appendChild(cardsContainer);
  staggerIn(Array.from(cardsContainer.children), 400, 200);

  return container;
}

function renderCode(episode) {
  const container = document.createElement('div');
  container.style.cssText = 'padding:40px 24px;max-width:640px;margin:0 auto';

  const header = renderEpisodeHeader(episode);
  container.appendChild(header);

  const codeBlock = document.createElement('div');
  codeBlock.style.cssText = "background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px 28px;font-family:'JetBrains Mono',monospace;font-size:clamp(12px,1.8vw,14px);line-height:1.8;overflow-x:auto";

  const linesContainer = document.createElement('div');

  episode.content.lines.forEach(line => {
    if (line.type === 'blank') {
      const blank = document.createElement('div');
      blank.style.height = '10px';
      linesContainer.appendChild(blank);
      return;
    }

    const lineEl = document.createElement('div');
    lineEl.style.whiteSpace = 'pre';
    lineEl.style.color = line.type === 'keyword' ? '#8af' : line.type === 'example' ? '#7c7' : '#bbb';

    if (line.type === 'keyword') {
      const keyword = document.createElement('span');
      keyword.style.cssText = 'color:#f8a;font-weight:600';
      keyword.textContent = line.text;
      lineEl.appendChild(keyword);

      const value = document.createElement('span');
      value.style.color = '#ddd';
      value.textContent = line.value;
      lineEl.appendChild(value);
    } else {
      lineEl.textContent = line.text;
    }

    linesContainer.appendChild(lineEl);
  });

  codeBlock.appendChild(linesContainer);
  container.appendChild(codeBlock);

  const note = document.createElement('p');
  note.style.cssText = "margin-top:24px;font-size:14px;color:#777;line-height:1.65;font-family:'Inter',sans-serif;font-style:italic";
  note.textContent = episode.content.note;
  container.appendChild(note);

  setTimeout(() => fadeIn(codeBlock, 300), 0);
  setTimeout(() => {
    staggerIn(Array.from(linesContainer.children), 500, 80);
  }, 300);
  setTimeout(() => fadeIn(note, 1800), 0);

  return container;
}

function renderPillars(episode) {
  const container = document.createElement('div');
  container.style.cssText = 'padding:40px 24px;max-width:640px;margin:0 auto';

  const header = renderEpisodeHeader(episode);
  container.appendChild(header);

  const pillarsContainer = document.createElement('div');
  pillarsContainer.style.cssText = 'display:flex;flex-direction:column;gap:0';

  episode.content.forEach((p, i) => {
    const pillar = document.createElement('div');
    pillar.style.cssText = `display:flex;gap:20px;padding:20px 0;border-bottom:${i < episode.content.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none'}`;

    const num = document.createElement('div');
    num.style.cssText = "font-size:32px;font-weight:300;color:rgba(138,170,255,0.3);font-family:'Inter',sans-serif;min-width:48px;line-height:1";
    num.textContent = p.num;
    pillar.appendChild(num);

    const content = document.createElement('div');

    const name = document.createElement('div');
    name.style.cssText = "font-size:15px;font-weight:600;color:#ddd;font-family:'JetBrains Mono',monospace;margin-bottom:6px";
    name.textContent = p.name;
    content.appendChild(name);

    const desc = document.createElement('div');
    desc.style.cssText = "font-size:14px;color:#888;line-height:1.65;font-family:'Inter',sans-serif";
    desc.textContent = p.desc;
    content.appendChild(desc);

    pillar.appendChild(content);
    pillarsContainer.appendChild(pillar);
  });

  container.appendChild(pillarsContainer);
  staggerIn(Array.from(pillarsContainer.children), 400, 180);

  return container;
}

function renderLandmarks(episode) {
  const container = document.createElement('div');
  container.style.cssText = 'padding:40px 24px;max-width:640px;margin:0 auto';

  const header = renderEpisodeHeader(episode);
  container.appendChild(header);

  const intro = document.createElement('p');
  intro.style.cssText = "font-size:clamp(14px,1.8vw,15px);color:#bbb;line-height:1.7;font-family:'Inter',sans-serif;margin-bottom:24px";
  intro.textContent = episode.content.intro;
  container.appendChild(intro);
  fadeIn(intro, 300);

  const reqLabel = document.createElement('div');
  reqLabel.style.cssText = "font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#8af;font-family:'Inter',sans-serif;font-weight:600;margin-bottom:14px";
  reqLabel.textContent = 'Required';
  container.appendChild(reqLabel);
  fadeIn(reqLabel, 500);

  const reqContainer = document.createElement('div');
  reqContainer.style.cssText = 'display:flex;flex-direction:column;gap:6px;margin-bottom:24px';

  episode.content.required.forEach(item => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:10px;align-items:baseline';

    const kw = document.createElement('span');
    kw.style.cssText = "color:#f8a;font-weight:600;font-size:13px;min-width:100px;font-family:'JetBrains Mono',monospace";
    kw.textContent = item.kw;
    row.appendChild(kw);

    const desc = document.createElement('span');
    desc.style.cssText = "color:#bbb;font-size:13px;line-height:1.5;font-family:'Inter',sans-serif";
    desc.textContent = item.desc;
    row.appendChild(desc);

    reqContainer.appendChild(row);
  });

  container.appendChild(reqContainer);
  staggerIn(Array.from(reqContainer.children), 600, 80);

  const optLabel = document.createElement('div');
  optLabel.style.cssText = "font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#555;font-family:'Inter',sans-serif;font-weight:600;margin-bottom:14px";
  optLabel.textContent = 'Optional';
  container.appendChild(optLabel);
  fadeIn(optLabel, 1100);

  const optContainer = document.createElement('div');
  optContainer.style.cssText = 'display:flex;flex-direction:column;gap:6px;margin-bottom:24px';

  episode.content.optional.forEach(item => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:10px;align-items:baseline';

    const kw = document.createElement('span');
    kw.style.cssText = "color:#6688bb;font-weight:600;font-size:13px;min-width:120px;font-family:'JetBrains Mono',monospace";
    kw.textContent = item.kw;
    row.appendChild(kw);

    const desc = document.createElement('span');
    desc.style.cssText = "color:#bbb;font-size:13px;line-height:1.5;font-family:'Inter',sans-serif";
    desc.textContent = item.desc;
    row.appendChild(desc);

    optContainer.appendChild(row);
  });

  container.appendChild(optContainer);
  staggerIn(Array.from(optContainer.children), 1200, 80);

  const footnote = document.createElement('p');
  footnote.style.cssText = "font-size:13px;color:#777;line-height:1.6;font-family:'Inter',sans-serif;font-style:italic";
  footnote.textContent = episode.content.footnote;
  container.appendChild(footnote);
  fadeIn(footnote, 1900);

  return container;
}

function renderPlanner(episode) {
  const container = document.createElement('div');
  container.style.cssText = 'padding:40px 24px;max-width:640px;margin:0 auto';

  const header = renderEpisodeHeader(episode);
  container.appendChild(header);

  const intro = document.createElement('p');
  intro.style.cssText = "font-size:clamp(15px,2vw,17px);color:#ccc;line-height:1.75;font-family:'Inter',sans-serif;margin-bottom:12px";
  intro.textContent = episode.content.intro;
  container.appendChild(intro);
  fadeIn(intro, 300);

  const philosophy = document.createElement('p');
  philosophy.style.cssText = "font-size:clamp(15px,2vw,17px);color:#999;line-height:1.75;font-family:'Inter',sans-serif;margin-bottom:28px";
  philosophy.textContent = episode.content.philosophy;
  container.appendChild(philosophy);
  fadeIn(philosophy, 700);

  const stepsContainer = document.createElement('div');
  stepsContainer.style.cssText = 'display:flex;flex-direction:column;gap:14px';

  episode.content.steps.forEach(step => {
    const stepEl = document.createElement('div');
    stepEl.style.cssText = 'display:flex;gap:18px;align-items:flex-start;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:18px 22px';

    const icon = document.createElement('span');
    icon.style.cssText = 'font-size:22px;min-width:32px;text-align:center;color:#8af;line-height:1';
    icon.textContent = step.icon;
    stepEl.appendChild(icon);

    const text = document.createElement('span');
    text.style.cssText = "font-size:15px;color:#aaa;line-height:1.6;font-family:'Inter',sans-serif";
    text.textContent = step.text;
    stepEl.appendChild(text);

    stepsContainer.appendChild(stepEl);
  });

  container.appendChild(stepsContainer);
  staggerIn(Array.from(stepsContainer.children), 1000, 200);

  const closing = document.createElement('p');
  closing.style.cssText = "font-size:14px;color:#777;line-height:1.65;margin-top:24px;font-family:'Inter',sans-serif;font-style:italic";
  closing.textContent = episode.content.closing;
  container.appendChild(closing);
  fadeIn(closing, 2000);

  const ctaContainer = document.createElement('div');
  ctaContainer.style.cssText = 'display:flex;justify-content:center;margin-top:32px';

  const cta = document.createElement('a');
  cta.href = episode.content.cta.url;
  cta.target = '_blank';
  cta.rel = 'noopener noreferrer';
  cta.style.cssText = "display:inline-flex;align-items:center;gap:10px;background:linear-gradient(135deg,rgba(138,170,255,0.15),rgba(138,170,255,0.08));border:1px solid rgba(138,170,255,0.3);border-radius:12px;padding:16px 36px;text-decoration:none;font-family:'JetBrains Mono',monospace;font-size:15px;color:#8af;font-weight:600;letter-spacing:0.5px;transition:all 0.3s;cursor:pointer";
  cta.innerHTML = `${episode.content.cta.text} <span style="font-size:18px">→</span>`;

  cta.addEventListener('mouseenter', () => {
    cta.style.background = 'linear-gradient(135deg,rgba(138,170,255,0.25),rgba(138,170,255,0.15))';
    cta.style.borderColor = 'rgba(138,170,255,0.5)';
  });
  cta.addEventListener('mouseleave', () => {
    cta.style.background = 'linear-gradient(135deg,rgba(138,170,255,0.15),rgba(138,170,255,0.08))';
    cta.style.borderColor = 'rgba(138,170,255,0.3)';
  });

  ctaContainer.appendChild(cta);
  container.appendChild(ctaContainer);
  fadeIn(ctaContainer, 2400);

  return container;
}

function renderEpisodeHeader(episode) {
  const header = document.createElement('div');
  header.style.cssText = 'margin-bottom:32px';

  const label = document.createElement('div');
  label.style.cssText = "font-size:11px;letter-spacing:4px;text-transform:uppercase;color:#8af;font-family:'JetBrains Mono',monospace;margin-bottom:10px";
  label.textContent = episode.label;
  header.appendChild(label);

  const title = document.createElement('h2');
  title.style.cssText = "font-size:clamp(28px,5vw,38px);font-weight:400;color:#f0f0f0;font-family:'Inter',sans-serif;margin:0;line-height:1.2";
  title.textContent = episode.title;
  header.appendChild(title);

  const subtitle = document.createElement('p');
  subtitle.style.cssText = "font-size:14px;color:#666;font-family:'JetBrains Mono',monospace;margin-top:6px";
  subtitle.textContent = episode.subtitle;
  header.appendChild(subtitle);

  fadeIn(header, 100);

  return header;
}

function renderEpisode(episode) {
  switch (episode.type) {
    case 'hero': return renderHero();
    case 'text': return renderText(episode);
    case 'cards': return renderCards(episode);
    case 'code': return renderCode(episode);
    case 'pillars': return renderPillars(episode);
    case 'landmarks': return renderLandmarks(episode);
    case 'planner': return renderPlanner(episode);
    default: return document.createElement('div');
  }
}

// Navigation
function goTo(idx) {
  if (idx === state.current || state.transitioning || idx < 0 || idx >= EPISODES.length) return;

  state.direction = idx > state.current ? 1 : -1;
  state.transitioning = true;

  const content = document.getElementById('episode-content');
  content.style.opacity = '0';
  content.style.transform = `translateY(${state.direction * 30}px)`;

  setTimeout(() => {
    state.current = idx;
    updateUI();
    state.transitioning = false;
  }, 350);
}

function next() {
  if (state.current < EPISODES.length - 1) goTo(state.current + 1);
}

function prev() {
  if (state.current > 0) goTo(state.current - 1);
}

function updateUI() {
  // Update progress bars
  document.querySelectorAll('.progress-bar').forEach((bar, i) => {
    if (i === state.current) {
      bar.style.background = '#8af';
    } else if (i < state.current) {
      bar.style.background = 'rgba(138,170,255,0.3)';
    } else {
      bar.style.background = 'rgba(255,255,255,0.08)';
    }
  });

  // Update labels
  document.getElementById('episode-number').textContent = `${state.current + 1} / ${EPISODES.length}`;
  document.getElementById('episode-label').textContent = EPISODES[state.current].label;

  // Update dots
  document.querySelectorAll('.nav-dot').forEach((dot, i) => {
    dot.style.background = i === state.current ? '#8af' : 'rgba(255,255,255,0.12)';
  });

  // Update buttons
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');

  prevBtn.disabled = state.current === 0;
  prevBtn.style.color = state.current === 0 ? '#333' : '#888';
  prevBtn.style.cursor = state.current === 0 ? 'default' : 'pointer';

  nextBtn.disabled = state.current === EPISODES.length - 1;
  nextBtn.style.background = state.current === EPISODES.length - 1 ? 'none' : 'rgba(138,170,255,0.1)';
  nextBtn.style.color = state.current === EPISODES.length - 1 ? '#333' : '#8af';
  nextBtn.style.cursor = state.current === EPISODES.length - 1 ? 'default' : 'pointer';

  // Render content
  const content = document.getElementById('episode-content');
  content.innerHTML = '';
  const episode = renderEpisode(EPISODES[state.current]);
  content.appendChild(episode);

  // Fade in
  setTimeout(() => {
    content.style.opacity = '1';
    content.style.transform = 'translateY(0)';
  }, 50);
}

// Initialize
function init() {
  const root = document.getElementById('root');

  // Create structure
  const app = document.createElement('div');
  app.style.cssText = 'background:#0c0e14;color:#ccc;min-height:100vh;font-family:"Inter",sans-serif;display:flex;flex-direction:column;position:relative;overflow:hidden';

  // Background grain
  const grain = document.createElement('div');
  grain.style.cssText = 'position:fixed;inset:0;opacity:0.03;pointer-events:none;background-image:url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")';
  app.appendChild(grain);

  // Top progress bar
  const progressBar = document.createElement('div');
  progressBar.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:10;display:flex;gap:4px;padding:12px 16px;background:linear-gradient(to bottom,rgba(12,14,20,0.95),transparent)';

  EPISODES.forEach((ep, i) => {
    const bar = document.createElement('button');
    bar.className = 'progress-bar';
    bar.style.cssText = 'flex:1;height:3px;border:none;border-radius:2px;cursor:pointer;background:rgba(255,255,255,0.08);transition:all 0.4s';
    bar.onclick = () => goTo(i);
    progressBar.appendChild(bar);
  });

  app.appendChild(progressBar);

  // Breadcrumb return link
  const breadcrumb = document.createElement('a');
  breadcrumb.href = '/';
  breadcrumb.style.cssText = "position:fixed;top:22px;left:16px;z-index:10;font-size:10px;letter-spacing:1px;color:#555;font-family:'JetBrains Mono',monospace;text-decoration:none;transition:color 0.2s;display:flex;align-items:center;gap:6px";
  breadcrumb.innerHTML = '<span style="font-size:12px">←</span><span>simplex-spec.org</span>';
  breadcrumb.addEventListener('mouseenter', () => breadcrumb.style.color = '#8af');
  breadcrumb.addEventListener('mouseleave', () => breadcrumb.style.color = '#555');
  app.appendChild(breadcrumb);

  // Episode labels
  const labels = document.createElement('div');
  labels.style.cssText = 'position:fixed;top:22px;right:16px;z-index:10;display:flex;gap:16px;align-items:center';

  const numLabel = document.createElement('span');
  numLabel.id = 'episode-number';
  numLabel.style.cssText = "font-size:10px;letter-spacing:2px;color:#555;font-family:'JetBrains Mono',monospace";
  labels.appendChild(numLabel);

  const epLabel = document.createElement('span');
  epLabel.id = 'episode-label';
  epLabel.style.cssText = "font-size:10px;letter-spacing:2px;color:#555;font-family:'JetBrains Mono',monospace";
  labels.appendChild(epLabel);

  app.appendChild(labels);

  // Main content
  const content = document.createElement('div');
  content.id = 'episode-content';
  content.style.cssText = 'flex:1;display:flex;flex-direction:column;justify-content:center;min-height:100vh;padding-top:48px;padding-bottom:80px;opacity:1;transform:translateY(0);transition:all 0.35s cubic-bezier(0.25,0.46,0.45,0.94)';
  app.appendChild(content);

  // Navigation
  const nav = document.createElement('div');
  nav.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:10;display:flex;justify-content:space-between;align-items:center;padding:16px 24px;background:linear-gradient(to top,rgba(12,14,20,0.95),transparent)';

  const prevBtn = document.createElement('button');
  prevBtn.id = 'prev-btn';
  prevBtn.textContent = '← prev';
  prevBtn.style.cssText = "background:none;border:1px solid rgba(255,255,255,0.1);color:#888;border-radius:8px;padding:10px 20px;cursor:pointer;font-family:'JetBrains Mono',monospace;font-size:12px;transition:all 0.3s";
  prevBtn.onclick = prev;
  nav.appendChild(prevBtn);

  const dots = document.createElement('div');
  dots.style.cssText = 'display:flex;gap:8px';

  EPISODES.forEach((_, i) => {
    const dot = document.createElement('div');
    dot.className = 'nav-dot';
    dot.style.cssText = 'width:6px;height:6px;border-radius:50%;cursor:pointer;background:rgba(255,255,255,0.12);transition:all 0.3s';
    dot.onclick = () => goTo(i);
    dots.appendChild(dot);
  });

  nav.appendChild(dots);

  const nextBtn = document.createElement('button');
  nextBtn.id = 'next-btn';
  nextBtn.textContent = 'next →';
  nextBtn.style.cssText = "background:rgba(138,170,255,0.1);border:1px solid rgba(138,170,255,0.2);color:#8af;border-radius:8px;padding:10px 20px;cursor:pointer;font-family:'JetBrains Mono',monospace;font-size:12px;transition:all 0.3s";
  nextBtn.onclick = next;
  nav.appendChild(nextBtn);

  app.appendChild(nav);

  // Add styles
  const style = document.createElement('style');
  style.textContent = `
    @keyframes pulse { 0%,100%{opacity:0.5} 50%{opacity:1} }
    ::-webkit-scrollbar { width: 0; }
    * { box-sizing: border-box; }
  `;
  document.head.appendChild(style);

  root.appendChild(app);

  // Keyboard controls
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); next(); }
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); prev(); }
  });

  // Initial render
  updateUI();
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
