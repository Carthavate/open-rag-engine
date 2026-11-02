/** The people who made Open RAG, shown in the Credits sheet. The desktop window opens only links on its own list
 * (ExternalLinks in OpenRag.Core), and a test there checks that every link here is on it. */

export type Credit = {
  name: string;
  initials: string;
  role: string;
  github: string;
  linkedin: string;
};

export const CREDITS: readonly Credit[] = [
  {
    name: "Wadi Touil",
    initials: "WT",
    role: "Embedded Systems Engineer",
    github: "https://github.com/TWadi",
    linkedin: "https://www.linkedin.com/in/wadi-touil-117472319/",
  },
  {
    name: "Ghassen Jamoussi",
    initials: "GJ",
    role: "Embedded Systems Developer",
    github: "https://github.com/GhassenJamoussi99",
    linkedin: "https://www.linkedin.com/in/ghassen-jamoussi/",
  },
];

export const SOURCE_URL = "https://github.com/Carthavate/open-rag-engine";
