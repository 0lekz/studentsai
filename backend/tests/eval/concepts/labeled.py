"""Five synthetic lectures of one cell biology course, with the concepts each section teaches.

Two terse sections fall between 20 and 40 tokens, like a slide with a title and
one bullet, and two logistics sections are short enough to be skipped.

`Mention.extracted_as` is the spelling the scripted fake returns for a labeled
concept; where it differs from the label it exercises deduplication. Labels
carry aliases, so a real model's reasonable spelling still matches.
"""

from dataclasses import dataclass, field

COURSE_NAME = "Cell biology"


@dataclass(frozen=True)
class Label:
    name: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Mention:
    label: str
    extracted_as: str
    description: str


@dataclass(frozen=True)
class Section:
    heading: str
    text: str
    mentions: tuple[Mention, ...] = ()


@dataclass(frozen=True)
class Lecture:
    filename: str
    title: str
    sections: tuple[Section, ...]

    @property
    def labels(self) -> set[str]:
        return {
            mention.label for section in self.sections for mention in section.mentions
        }

    def html(self) -> str:
        body = "".join(
            f"<h2>{section.heading}</h2><p>{section.text}</p>"
            for section in self.sections
        )
        return f"<h1>{self.title}</h1>{body}"


@dataclass(frozen=True)
class LabeledSet:
    course_name: str
    lectures: tuple[Lecture, ...]
    labels: dict[str, Label] = field(default_factory=dict)

    def section(self, heading: str) -> Section | None:
        for lecture in self.lectures:
            for section in lecture.sections:
                if section.heading == heading:
                    return section
        return None


def _m(label: str, description: str, extracted_as: str | None = None) -> Mention:
    return Mention(label, extracted_as or label, description)


LABELS = {
    label.name: label
    for label in (
        Label("Cell theory"),
        Label("Prokaryotic cell", ("Prokaryote",)),
        Label("Eukaryotic cell", ("Eukaryote",)),
        Label("Plasma membrane", ("Cell membrane",)),
        Label("Phospholipid bilayer", ("Lipid bilayer",)),
        Label("Fluid mosaic model"),
        Label("Diffusion", ("Simple diffusion",)),
        Label("Osmosis"),
        Label("Active transport"),
        Label("Sodium-potassium pump", ("Na+/K+ pump", "Sodium potassium ATPase")),
        Label("Metabolism"),
        Label("Anabolism", ("Anabolic pathway",)),
        Label("Catabolism", ("Catabolic pathway",)),
        Label("ATP", ("Adenosine triphosphate",)),
        Label("ATP hydrolysis"),
        Label("Enzyme"),
        Label("Activation energy"),
        Label("Active site"),
        Label("Competitive inhibition", ("Competitive inhibitor",)),
        Label("Cofactor"),
        Label("Coenzyme"),
        Label("Glycolysis"),
        Label("Pyruvate"),
        Label("Krebs cycle", ("Citric acid cycle", "TCA cycle")),
        Label("Acetyl-CoA", ("Acetyl coenzyme A",)),
        Label("NADH"),
        Label("Electron transport chain", ("ETC",)),
        Label("ATP synthase"),
        Label("Chemiosmosis"),
        Label("Mitochondrion", ("Mitochondria",)),
        Label("Photosynthesis"),
        Label("Chloroplast"),
        Label("Chlorophyll"),
        Label("Light-dependent reactions", ("Light reactions",)),
        Label("Photosystem II"),
        Label("Calvin cycle", ("Light-independent reactions",)),
        Label("Carbon fixation"),
        Label("RuBisCO", ("Ribulose bisphosphate carboxylase",)),
        Label("Cell cycle"),
        Label("Interphase"),
        Label("DNA replication"),
        Label("Mitosis"),
        Label("Sister chromatids", ("Sister chromatid",)),
        Label("Meiosis"),
        Label("Crossing over"),
        Label("Gamete"),
        Label("Cytokinesis"),
        Label("Cleavage furrow"),
    )
}

LECTURES = (
    Lecture(
        "week1-cells-and-membranes.pdf",
        "Cells and membranes",
        (
            Section(
                "Cell theory",
                "Cell theory states that every living thing is made of cells, that the cell is the "
                "basic unit of life, and that new cells arise only from existing cells. Prokaryotic "
                "cells, such as bacteria, have no nucleus and keep their DNA in the cytoplasm. "
                "Eukaryotic cells keep their DNA in a membrane-bound nucleus and contain organelles.",
                (
                    _m(
                        "Cell theory",
                        "Every living thing is made of cells, which arise only from existing cells.",
                    ),
                    _m(
                        "Prokaryotic cell",
                        "A cell without a nucleus, such as a bacterium.",
                    ),
                    _m(
                        "Eukaryotic cell",
                        "A cell whose DNA sits in a membrane-bound nucleus.",
                    ),
                ),
            ),
            Section(
                "The plasma membrane",
                "The plasma membrane separates the cell from its surroundings. It is a phospholipid "
                "bilayer: two layers of phospholipids whose hydrophobic tails face each other. The "
                "fluid mosaic model describes the membrane as a fluid layer in which proteins float "
                "and move sideways.",
                (
                    _m(
                        "Plasma membrane",
                        "The boundary that separates the cell from its surroundings.",
                    ),
                    _m(
                        "Phospholipid bilayer",
                        "Two layers of phospholipids with their hydrophobic tails facing each other.",
                    ),
                    _m(
                        "Fluid mosaic model",
                        "The membrane as a fluid layer in which proteins float and move.",
                    ),
                ),
            ),
            Section(
                "Membrane transport",
                "Diffusion moves molecules from high to low concentration without energy. Osmosis is "
                "the diffusion of water across a selectively permeable membrane. Active transport "
                "moves molecules against their gradient and spends ATP; the sodium-potassium pump "
                "exports three sodium ions and imports two potassium ions per ATP.",
                (
                    _m(
                        "Diffusion",
                        "Movement of molecules from high to low concentration without energy.",
                    ),
                    _m(
                        "Osmosis",
                        "Diffusion of water across a selectively permeable membrane.",
                    ),
                    _m(
                        "Active transport",
                        "Moving molecules against their gradient by spending ATP.",
                    ),
                    _m(
                        "Sodium-potassium pump",
                        "A pump exporting three sodium ions and importing two potassium ions per ATP.",
                    ),
                ),
            ),
            Section("Reading for week 1", "Read chapter 3 before Friday."),
        ),
    ),
    Lecture(
        "week2-energy-and-enzymes.pdf",
        "Energy and enzymes",
        (
            Section(
                "Metabolism",
                "Metabolism is the sum of the chemical reactions in a cell. Anabolism builds large "
                "molecules from small ones and consumes energy, while catabolism breaks large "
                "molecules down and releases energy that the cell can capture.",
                (
                    _m("Metabolism", "The sum of the chemical reactions in a cell."),
                    _m(
                        "Anabolism",
                        "Building large molecules from small ones, consuming energy.",
                    ),
                    _m(
                        "Catabolism", "Breaking large molecules down, releasing energy."
                    ),
                ),
            ),
            Section(
                "Energy currency",
                "Adenosine triphosphate, or ATP, is the energy currency of the cell. ATP hydrolysis "
                "removes the terminal phosphate group and releases energy that drives work such as "
                "muscle contraction and active transport by the sodium potassium pump.",
                (
                    _m(
                        "ATP",
                        "Adenosine triphosphate, the energy currency of the cell.",
                    ),
                    _m(
                        "ATP hydrolysis",
                        "Removing ATP's terminal phosphate to release energy for work.",
                    ),
                    _m(
                        "Active transport",
                        "Work driven by the energy of ATP hydrolysis.",
                        "active transport",
                    ),
                    _m(
                        "Sodium-potassium pump",
                        "A transporter powered by ATP hydrolysis.",
                        "Sodium potassium pump",
                    ),
                ),
            ),
            Section(
                "Enzymes",
                "An enzyme is a protein catalyst that speeds up a reaction by lowering its activation "
                "energy, the energy needed to start the reaction. The substrate binds at the active "
                "site. In competitive inhibition, a molecule resembling the substrate occupies the "
                "active site and blocks it.",
                (
                    _m("Enzyme", "A protein catalyst that speeds up a reaction."),
                    _m("Activation energy", "The energy needed to start a reaction."),
                    _m("Active site", "Where the substrate binds on an enzyme."),
                    _m(
                        "Competitive inhibition",
                        "A substrate look-alike occupies and blocks the active site.",
                    ),
                ),
            ),
            Section(
                "Cofactors",
                "Cofactors are non-protein helpers some enzymes need; organic cofactors are coenzymes.",
                (
                    _m("Cofactor", "A non-protein helper some enzymes need."),
                    _m("Coenzyme", "An organic cofactor."),
                ),
            ),
        ),
    ),
    Lecture(
        "week3-cellular-respiration.pdf",
        "Cellular respiration",
        (
            Section(
                "Glycolysis",
                "Glycolysis splits one glucose molecule into two molecules of pyruvate in the "
                "cytoplasm. It needs no oxygen and yields a net gain of two ATP and two NADH per "
                "glucose. Pyruvate then enters the mitochondrion if oxygen is present.",
                (
                    _m(
                        "Glycolysis",
                        "Splitting glucose into two pyruvate in the cytoplasm for a net two ATP.",
                    ),
                    _m("Pyruvate", "The three-carbon product of glycolysis."),
                    _m("ATP", "The energy currency glycolysis yields.", "Atp"),
                ),
            ),
            Section(
                "Krebs cycle",
                "In the mitochondrial matrix, pyruvate is converted to acetyl-CoA, which enters the "
                "Krebs cycle. Each turn of the cycle releases two carbon dioxide molecules and loads "
                "electrons onto NADH, the carrier that takes them to the next stage.",
                (
                    _m(
                        "Krebs cycle",
                        "The cycle in the matrix that oxidizes acetyl-CoA to carbon dioxide.",
                    ),
                    _m(
                        "Acetyl-CoA",
                        "The molecule pyruvate becomes before entering the Krebs cycle.",
                    ),
                    _m("NADH", "The electron carrier loaded by the Krebs cycle."),
                ),
            ),
            Section(
                "Oxidative phosphorylation",
                "The electron transport chain in the inner membrane of the mitochondria passes "
                "electrons from NADH to oxygen and pumps protons across the membrane. Protons flow "
                "back through ATP synthase, which makes ATP; this coupling is called chemiosmosis.",
                (
                    _m(
                        "Electron transport chain",
                        "Membrane proteins that pass electrons to oxygen and pump protons.",
                    ),
                    _m(
                        "Mitochondrion",
                        "The organelle whose inner membrane holds the electron transport chain.",
                        "Mitochondria",
                    ),
                    _m(
                        "ATP synthase",
                        "The enzyme that makes ATP as protons flow back through it.",
                    ),
                    _m(
                        "Chemiosmosis", "Coupling the proton gradient to ATP synthesis."
                    ),
                ),
            ),
        ),
    ),
    Lecture(
        "week4-photosynthesis.pdf",
        "Photosynthesis",
        (
            Section(
                "Overview of photosynthesis",
                "Photosynthesis converts light energy into chemical energy stored in sugar. It takes "
                "place in the chloroplast, an organelle that, like the mitochondrion, has its own DNA. "
                "Chlorophyll is the green pigment in the chloroplast that absorbs red and blue light.",
                (
                    _m(
                        "Photosynthesis",
                        "Converting light energy into chemical energy stored in sugar.",
                    ),
                    _m(
                        "Chloroplast", "The organelle where photosynthesis takes place."
                    ),
                    _m(
                        "Mitochondrion",
                        "An organelle with its own DNA, like the chloroplast.",
                        "mitochondrion",
                    ),
                    _m(
                        "Chlorophyll",
                        "The green pigment that absorbs red and blue light.",
                    ),
                ),
            ),
            Section(
                "Light reactions",
                "The light-dependent reactions run in the thylakoid membranes. Photosystem II absorbs "
                "light and splits water, releasing oxygen. The electrons drive a proton gradient, and "
                "ATP synthase in the thylakoid membrane makes ATP, just as in the mitochondrion.",
                (
                    _m(
                        "Light-dependent reactions",
                        "Reactions in the thylakoid membranes driven by light.",
                        "Light dependent reactions",
                    ),
                    _m(
                        "Photosystem II",
                        "The photosystem that absorbs light and splits water.",
                    ),
                    _m(
                        "ATP synthase",
                        "The enzyme in the thylakoid membrane that makes ATP.",
                    ),
                ),
            ),
            Section(
                "Calvin cycle",
                "The Calvin cycle uses ATP and NADPH from the light reactions to build sugar in the "
                "stroma. Its first step is carbon fixation: the enzyme RuBisCO attaches carbon dioxide "
                "to a five-carbon sugar. RuBisCO is thought to be the most abundant protein on Earth.",
                (
                    _m(
                        "Calvin cycle",
                        "Building sugar in the stroma with ATP and NADPH.",
                    ),
                    _m(
                        "Carbon fixation",
                        "Attaching carbon dioxide to a five-carbon sugar.",
                    ),
                    _m(
                        "RuBisCO",
                        "The enzyme that fixes carbon dioxide in the Calvin cycle.",
                    ),
                ),
            ),
        ),
    ),
    Lecture(
        "week5-cell-division.pdf",
        "Cell division",
        (
            Section(
                "The cell cycle",
                "The cell cycle is the sequence of growth and division a cell goes through. Most of "
                "it is interphase, when the cell grows and DNA replication copies every chromosome "
                "so that each copy is made of two identical sister chromatids.",
                (
                    _m(
                        "Cell cycle",
                        "The sequence of growth and division a cell goes through.",
                    ),
                    _m(
                        "Interphase",
                        "The part of the cell cycle when the cell grows and copies its DNA.",
                    ),
                    _m("DNA replication", "Copying every chromosome before division."),
                    _m(
                        "Sister chromatids",
                        "The two identical copies a replicated chromosome is made of.",
                    ),
                ),
            ),
            Section(
                "Mitosis",
                "Mitosis divides the nucleus so that each daughter cell receives one copy of every "
                "chromosome. The sister chromatids line up at the middle of the cell and are pulled "
                "apart, producing two genetically identical daughter cells.",
                (
                    _m(
                        "Mitosis",
                        "Nuclear division producing two genetically identical daughter cells.",
                    ),
                    _m(
                        "Sister chromatids",
                        "Identical copies pulled apart during mitosis.",
                        "sister chromatids",
                    ),
                ),
            ),
            Section(
                "Meiosis",
                "Meiosis is the division that makes gametes, such as sperm and egg cells. It halves the "
                "chromosome number in two rounds of division. During crossing over, paired chromosomes "
                "exchange segments, so every gamete carries a new combination of alleles.",
                (
                    _m(
                        "Meiosis",
                        "Division that halves the chromosome number to make gametes.",
                    ),
                    _m("Gamete", "A sex cell such as a sperm or an egg."),
                    _m(
                        "Crossing over",
                        "Paired chromosomes exchanging segments during meiosis.",
                    ),
                ),
            ),
            Section(
                "Cytokinesis",
                "Cytokinesis splits the cytoplasm after mitosis; a cleavage furrow pinches animal cells in two.",
                (
                    _m("Cytokinesis", "Splitting the cytoplasm after mitosis."),
                    _m(
                        "Cleavage furrow",
                        "The groove that pinches an animal cell in two.",
                    ),
                ),
            ),
            Section("Exam logistics", "The midterm covers weeks 1 to 5."),
        ),
    ),
)

LABELED_SET = LabeledSet(COURSE_NAME, LECTURES, LABELS)
