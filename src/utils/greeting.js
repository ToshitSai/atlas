/**
 * Dynamic local time-based greeting for Atlas.
 * Computes greetings based on browser local hour (0-23).
 */
export function getDynamicGreeting() {
  const hour = new Date().getHours();

  if (hour >= 5 && hour < 12) {
    const morningGreetings = [
      { main: "Good morning. What should we investigate?", sub: "Ready when you are. Ask anything or describe a research task." },
      { main: "Morning. What should we explore today?", sub: "Autonomous AI research workspace at your command." },
      { main: "Good morning. What's on your research agenda?", sub: "Evidence-aware research, experiments, and reports." },
    ];
    return morningGreetings[Math.floor(Math.random() * morningGreetings.length)];
  } else if (hour >= 12 && hour < 17) {
    const afternoonGreetings = [
      { main: "Good afternoon. What should we investigate?", sub: "Ready when you are. Ask anything or describe a research task." },
      { main: "Good afternoon. What problem shall we solve?", sub: "Explore datasets, design experiments, or ask direct questions." },
      { main: "Afternoon. Ready to launch an investigation?", sub: "Autonomous AI research workspace at your command." },
    ];
    return afternoonGreetings[Math.floor(Math.random() * afternoonGreetings.length)];
  } else if (hour >= 17 && hour < 22) {
    const eveningGreetings = [
      { main: "Good evening. What should we investigate?", sub: "Ready when you are. Ask anything or describe a research task." },
      { main: "Good evening. What topic shall we explore?", sub: "Evidence-aware research, experiments, and reports." },
      { main: "Evening. Ready for tonight's research?", sub: "Autonomous AI research workspace at your command." },
    ];
    return eveningGreetings[Math.floor(Math.random() * eveningGreetings.length)];
  } else {
    const nightGreetings = [
      { main: "Working late? What should we investigate?", sub: "Ready when you are. Ask anything or describe a research task." },
      { main: "Good night. What shall we analyze?", sub: "Deep research and experiment synthesis operating 24/7." },
      { main: "Late night session. What are we exploring?", sub: "Autonomous AI research workspace at your command." },
    ];
    return nightGreetings[Math.floor(Math.random() * nightGreetings.length)];
  }
}

export const ROTATING_PLACEHOLDERS = [
  "Ask a direct question or describe a research task…",
  "Investigate a machine learning problem…",
  "Compare two models or algorithms…",
  "Research a topic, dataset, or paper…",
];
