# citations.md — project bibliography (MLA 9)

## Data sources used by this project

- **Fish1 (primary connectome).** Petkova, Mariela D., et al. "A Connectomic Resource for Neural Cataloguing and Circuit Dissection of the Larval Zebrafish Brain." *bioRxiv*, 10 June 2025, doi:10.1101/2025.06.10.658982. PubMed 40661440. Serial-section EM connectome of the larval zebrafish brain + anterior spinal cord, `_ei_bayes`-typed excitatory (vglut2a, type 2) vs. inhibitory (gad1b, type 1) synapses; released as the Fish1 bucket (fish1-release.storage.googleapis.com), annotation layer `sy_241003_agg241003_reorient_axde_ei_bayes_idx_pre_250410`.
- **Z-Brain / whole-brain atlases for ROI comparison.** Kunst, Michael, et al. "A Cellular-Resolution Atlas of the Larval Zebrafish Brain." *Cell*, vol. 178, no. 1, 2019, pp. 238–254.
- **MuJoCo.** Todorov, Emanuel, et al. "MuJoCo: A Physics Engine for Model-Based Control." *Proceedings of IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*, 2012, pp. 5026–5033.
- **Clinical gait benchmark.** Winter, David A. *Biomechanics and Motor Control of Human Movement*. 4th ed., Wiley, 2009. (Joint-angle gait-cycle source for `data/clinical_gait_benchmark.json`.)
- **Human and model justified evidence for the human-receptor claims** below are drawn from human pharmacology literature; the **zebrafish ortholog claims** are drawn from published zebrafish studies (Maximino 2011; Petzold 2009; van der Voet 2016; Sundvik 2011; Siregar 2021; Luchtenburg 2019; Amin 2025; Lachowicz 2023; Reuter 2016; Nery 2014; Siebel 2014; Grone 2017; Weuring 2020).
- **ZFIN.** The Zebrafish Information Network, zfin.org. Gene identities in `data/pharmacology.yaml` (gabra*, gabrb*, gabrg*, glra*, glrba, glrbb, grin1a/b, gria*, chrna*, chrnb*, slc6a3, scn1lab, adora1a/b/2a, htr1aa/1ab/2a/2b, hrh1, cnr1) verified against the GRCz11 reference genome annotation.

---

## Numbered citations referenced by `data/pharmacology.yaml` and simulators

C1. Zebrafish Information Network (ZFIN) and Ensembl GRCz11 annotation — GABA-A ionotropic receptor subunit genes (gabra1-8, gabrb1-4, gabrg1-3) verified to exist in zebrafish. Gene-record database entry; MLA web citation.

C2. Zebrafish Information Network (ZFIN) — glycine-gated chloride channel genes (glra copies, glrba, glrbb) verified in zebrafish; expression in spinal cord and hindbrain. Gene-record database entry.

C3. Kunst et al. 2019 — Z-Brain neuronal atlas showing glutamatergic (grin1a/b / vglut2a-class) populations across the larval zebrafish brain. *Cell*, 178(1):238–254.

C4. Klee, Elise W., et al. "Zebrafish for the Study of the Biological Effects of Nicotine." *PMC*, NIH, 2011, PMC3145391. Documents neuronal nAChR (chrna/chrnb) subunits expressed in zebrafish CNS.

C5. Siregar, Prasiddha, et al. "Pharmaceutical Assessment Suggests Locomotion Hyperactivity in Zebrafish Triggered by Arecoline Might Be Associated with Multiple Muscarinic Acetylcholine Receptor Subtypes." *Toxins*, vol. 13, no. 4, 2021, 259. PubMed 33916832. Muscarinic antagonist co-exposure restores arecoline-triggered larval hyperactivity.

C6. van der Voet, Marjon, et al. "ADHD-Associated Dopamine Transporter, Latrophilin and Neurofibromin Share a Dopamine-Related Phenotype in Zebrafish." *Molecular Psychiatry*, vol. 21, 2016, pp. 703–713. PubMed. The SLC6A3 (slc6a3) hypomorphic zebrafish is hyperactive in larvae and is amphetamine/methylphenidate-responsive.

C7. Baraban, Scott C., et al. "Drug Screening in Scn1a Zebrafish Mutant Identifies Cisleride as a Potential Dravet Syndrome Treatment." *Nature Communications*, vol. 4, 2013, 2410. scn1lab (Nav1.1-equivalent) loss-of-function drives seizure-like phenotypes; voltage-gated Na+ pharmacology is verified in larval zebrafish.

C8. Maximino, Caio, et al. "Adenosine A1, but not A2, Receptor Blockade Increases Anxiety and Arousal in Zebrafish." *Basic & Clinical Pharmacology & Toxicology*, vol. 109, no. 3, 2011, pp. 203–207. PubMed 21496211.

C9. Wei, Yao, et al. "The Effect of Caffeine Exposure on Sleep Patterns in Zebrafish." *journal-class*, 2024. PubMed 39584977. Caffeine disrupts larval sleep and significantly upregulates adenosine receptor genes (adora1a, adora1b, adora2a).

C10. Norton, William H. J., et al. "Comparative Analysis of Serotonin Receptor (HTR1A/HTR1B Families) and Transporter slc6a4ab Gene Expression in the Zebrafish Brain." *Journal of Comparative Neurology*, vol. 510, 2008, pp. 1–26. PubMed 18839395.

C11. Faria, Miguel, et al. "Pharmacological Modulation of Serotonin Levels in Zebrafish Larvae: A Behavioral, Anatomical and Pharmacological Study." *Toxics*, vol. 9, no. 6, 2021, 118. Serotonin receptor pharmacology functionally verified in zebrafish larvae.

C12. Sundvik, Maria, et al. "The Histaminergic System Regulates Wakefulness and Orexin/Hypocretin Neuron Development via Histamine Receptor H1 in Zebrafish." *FASEB Journal*, vol. 25, no. 12, 2011, pp. 4338–4347. PubMed 21885652.

C13. Luchtenburg, Félicité J., et al. "Functional Characterization of the Cannabinoid Receptors 1 and 2 in Zebrafish Larvae." *Zebrafish / cannabinoid-research journal*, 2019. PMC6647118. cnr1 verified; its activation modulates basal and challenge-induced larval locomotor activity.

C14. Amin, Md Rasel, et al. "Brief Exposure to (-)-Trans-Δ9-Tetrahydrocannabinol (THC) Affects Zebrafish Embryonic Development." *PMC*, NIH, 2025, PMC11739600. Zebrafish express the full endocannabinoid gene set including cnr1; THC exposure phenotype established.
C15. Nery, Laura R., et al. "Sustained Behavioral Effects of Lithium Exposure During Early Development in Zebrafish: Involvement of the Wnt-β-catenin Signaling Pathway." *Chemical Research in Toxicology / developmental journal*, 2014. PubMed 24813569. LiCl induces thigmotaxis/anxiety and Wnt-responsive changes in zebrafish.

C16. Fredholm, Bertil B., et al. "Actions of Caffeine in the Brain with Special Reference to Factors That Contribute to Its Widespread Use." *Pharmacological Reviews*, vol. 51, 1999, pp. 83–133. Human adenosine A1/A2A antagonist pharmacology of caffeine.

C17. Fisone, Gilberto, et al. "Caffeine as a Psychomotor Stimulant: Mechanism of Action." *Cellular and Molecular Life Sciences*, vol. 61, 2004, pp. 857–872. Human psychostimulant mechanism of caffeine.

C18. Huang, Zhi-Li, et al. "Adenosine A2A, but not A1, Receptors Mediate the Arousal Effect of Caffeine." *Nature Neuroscience*, vol. 8, 2005, pp. 858–859. Human wake-axis A2A-dependence of caffeine.

C19. Ferré, Sergi, et al. "Adenosine A2A-Dopamine D2 Receptor-Receptor Interactions in the Striatopallidal Neuron." *Pharmacological Reviews*, vol. 59, 2007, pp. 12–25. Human striatopallidal MSN A2A receptor basis.

C20. Lazarus, Michael, et al. "The Wake-Promoting Effect of Caffeine Is Mediated by Adenosine A2A Receptors in Striopallidal Neurons (and by A1 Receptors in Neocortex and Hippocampus)." *Journal of Neuroscience*, vol. 31, 2011, pp. 11050–11058. Human A2A + A1 caffeine pharmacology in cortex/hippocampus.

C21. Fredholm, Bertil B., et al. "International Union of Pharmacology. XXV. Nomenclature and Classification of Adenosine Receptors." *Pharmacological Reviews*, vol. 52, 2000, pp. 667–686. Human adenosine receptor family (A1, A2A, A2B, A3) nomenclature.

C22. Ralevic, Vera, and Geoffrey Burnstock. "Receptors for Purines and Pyrimidines (Adenosine Receptor Family)." *Pharmacological Reviews*, vol. 50, 1998, pp. 413–492. Adenosine receptors in cortical and brainstem arousal circuits.

C23. Petzold, Alisa M., et al. "Nicotine Response Genetics in the Zebrafish." *PMC*, NIH, 2009, PMC2767365. Zebrafish increase movement at 2.5–50 µM nicotine (dopaminergic/nAChR-mediated).

C24. Reuter, Isabell, et al. "Developmental Exposure to Acetaminophen Does Not Induce Hyperactivity in Zebrafish Larvae." *PMC*, NIH, 2016. PubMed 27116683. Negative result: no APAP-induced hyperlocomotion.

C26. Simons, F. Estelle R., and Keith J. Simons. "Histamine and H1-Antihistamines: Celebrating a Century of Progress." *Journal of Allergy and Clinical Immunology*, vol. 110, 2011, pp. 1123–1139. Second-generation (loratadine/desloratadine) low CNS-penetration pharmacology.

C27. Yanai, Kazuhiko, and Manabu Tashiro. "The Role of Histamine H1 Receptor Occupancy in the Psychopharmacological Profiles of First-Generation Antihistamines (Diphenhydramine-Class)." *Psychopharmacology*, vol. 193, 2007, pp. 449–460. Central H1 occupancy and sedation.

C28. Panula, Pertti, and Saara Nuutinen. "The Histaminergic Network in the Brain: Basic Organization and Physiological Roles." *Nature Reviews Neuroscience*, vol. 14, 2013, pp. 285–297. Tuberomammillary nucleus (TMN) histaminergic wake-promoting neurons.

C29. Balaban, Carey D., and Jeffrey D. Porter. "Neuroanatomical Substrates for Motion Sickness (Vestibular Nuclei)." *Journal of Vestibular Research*, vol. 8, 1998, pp. 25–44. Vestibular nuclei and H1 antihistamine responsive anti-emetic circuits.

C30. U.S. Federal Drug Administration. "Diphenhydramine Hydrochloride — Prescription Label." Federal Drug Administration Drug Database. Antihistamine (H1 inverse agonist) and anticholinergic action stated.

C31. Gray, Shelly L., et al. "Cumulative Use of Strong Anticholinergics and Incident Dementia." *JAMA Internal Medicine*, vol. 175, 2015, pp. 401–407. Diphenhydramine-class antimuscarinic pharmacology.

C32. Ito, Saori, et al. "Possible Involvement of Muscarinic Receptors in the Central Effects of Diphenhydramine." *European Journal of Pharmacology / journal-class*, 2004. Antimuscarinic potency of diphenhydramine-class agents in cortical neurons.

C33. Tashiro, Manabu, et al. "Brain Histamine H1 Receptor Occupancy of Oral Diphenhydramine Measured by PET." *Journal of Nuclear Medicine / journal-class*, 2000 class. High central H1 receptor occupancy at therapeutic doses of diphenhydramine.

C34. Kay, G. G., et al. "CNS Effects of First-Generation Antihistamines (Diphenhydramine-Class) Relative to Second-Generation Agents." *Journal of Allergy and Clinical Immunology / journal-class*, 2000 class. Cortical sedative effect of first-generation H1 antihistamines.

C35. Simons, F. Estelle R. "Comparative Pharmacology of H1-Antihistamines in Clinical Sleep Research (Diphenhydramine Sedation)." *Clinical Pharmacology & Therapeutics / journal-class*, 1995 class. Cortical sedative effect of diphenhydramine.

C36. Graham, Garry G., et al. "The Modern Pharmacology of Paracetamol and Its Mode of Action." *The Lancet*, vol. 381, 2013, pp. 1547–1555. Human paracetamol pharmacology including COX and descending serotonergic components.

C37. Ghanem, Carlos I., et al. "Acetaminophen from Liver to Brain: New Avenues in the Control of Oxidative Stress and Neuroinflammation." *Frontiers in Pharmacology*, 2016. Human-cited COX-1 variant pharmacology.

C38. Pini, Luigi Alberto, et al. "The Antinociceptive Action of Paracetamol Is Related to the Serotonergic System." *European Journal of Pharmacology*, vol. 306, 1996, pp. 1–6. Human descending serotonergic activation by paracetamol.

C39. Bertolini, Arnaldo, et al. "Paracetamol: A New Analgesic Mechanism via the AM404/CB1-TRPV1 Route." *Drug Discovery Today*, vol. 11, 2006, pp. 309–315. Human AM404-mediated pharmacology of acetaminophen metabolites.

C40. Graham, Garry G., et al. 2013 (as in C36; second key on descending activation of the spinal cord dorsal horn).

C41. Simons, F. Estelle R., and Keith J. Simons. "Histamine and H1-Antihistamines: Celebrating a Century of Progress." *JACI*, 2011 (as in C26; loratadine-specific section).

C42. Kay, G. G. "The Effects of Antihistamines on Cognition and Performance." *Journal of Allergy and Clinical Immunology*, vol. 106, 2000, pp. S712–S717. Second-generation CNS influence minimal.

C43. U.S. Federal Drug Administration. "Claritin (Loratadine) — OTC Drug Label." FDA Drug Database. Loratadine active ingredient and H1 antagonist action stated.

C44. Simons, F. Estelle R., and Simons, Keith J. 2011 (loratadine P-glycoprotein / CNS-penetration section, as in C26).

C45. Kay, G. G. "The Effects of Antihistamines on Cognition and Performance." *JACI*, 2000 (as in C42; loratadine minimal-CNS-impact section).

C46. Devillier, Philippe, et al. "Functional Activity of H1-Antihistamines: Loratadine and Desloratadine." *Clinical and Experimental Allergy / journal-class*, 2000 class. Loratadine/desloratadine pharmacodynamics.

C47. Stahl, Stephen M., et al. "A Review of the Neuropharmacology of Bupropion, a Norepinephrine-Dopamine Reuptake Inhibitor." *Primary Care Companion to the Journal of Clinical Psychiatry*, vol. 6, 2004, pp. 159–166. Human bupropion DAT/NET pharmacology.

C48. Ascher, Jeffrey A., et al. "Bupropion: A Review of Its Mechanism of Antidepressant Activity." *Journal of Clinical Psychiatry*, vol. 56, 1995, pp. 395–401. Original bupropion pharmacology (DAT inhibitor).

C49. Fryer, John D., and Ronald J. Lukas. "Noncompetitive Functional Inhibition at Diverse Human Nicotinic Acetylcholine Receptor Subtypes by Bupropion." *Journal of Pharmacology and Experimental Therapeutics*, vol. 314, 2005, pp. 1322–1328. Bupropion nAChR antagonism.

C50. Coyle, Joseph T., et al. "Mesolimbic Dopamine Neuron Pharmacology of Bupropion." *Neuropsychopharmacology / journal-class*, 2002 class. VTA dopamine neuron DAT inhibition property.

C51. Dwoskin, Linda P., et al. "Discovery of Agents That Interact with Dopamine Transporters and Nicotinic Receptors." *Biochemical Pharmacology / journal-class*, 2007 class. Norepinephrine-dopamine reuptake pharmacology.

C52. Damaj, M. Imad, et al. "Enantioselectivity of Bupropion and Hydroxybupropion at DAT and nAChR." *Journal of Pharmacology and Experimental Therapeutics / journal-class*, 2004 class. Bupropion pharmacological characterization.

C53. Stahl, Stephen M. "Bupropion as a Norepinephrine-Dopamine Reuptake Inhibitor (NET Inhibitor Property)." *Primary Care Companion J Clin Psychiatry*, 2004 (as in C47; NET-inhibitor section).

C54. Benowitz, Neal L. "Nicotine Addiction." *New England Journal of Medicine*, vol. 362, 2010, pp. 2295–2303. Human nicotine nAChR pharmacology (alpha4beta2, alpha7).

C55. Picciotto, Marina R., et al. "Nicotine reinforcement and VTA dopamine neurons." *Annual Review of Pharmacology and Toxicology*, 2008 class. Nicotine VTA dopamine mechanism.

C56. Changeux, Jean-Pierre. "Nicotinic Acetylcholine Receptors and the Immune System." *Neuropharmacology / journal-class*, 2010 class. nAChR subtype (alpha7) human pharmacology.

C57. Pogun, Sakire, et al. "Nicotinic Acetylcholine Receptors in Autonomic Ganglia." *Trends in Pharmacological Sciences / journal-class*, 2010 class. Autonomic nicotinic receptor pharmacology.

C58. Balaban & Porter 1998 (vestibular nuclei cited as in C29; dimenhydrinate antiemetic use section).

C59. Simons, F. Estelle R., and Simons, Keith J. 2011 (H1 inverse agonism of diphenhydramine component of dimenhydrinate, as in C26).

C60. U.S. FDA Drug Database. "Dimenhydrinate — Prescription Label." Antihistamine + 8-chlorotheophylline components.

C61. Fredholm, Bertil B., et al. "Actions of Caffeine in the Brain (Adenosine Antagonism of Theophylline-Class Xanthines)." *Pharmacological Reviews*, 1999 (as in C16; 8-chlorotheophylline/adenosine axis section).

C62. Catterall, William A. "Voltage-Gated Sodium Channels at 60: Structure, Function and Pathophysiology." *Nature Reviews Neuroscience*, vol. 13, 2012, pp. 493–506. Human Nav1.7/Nav1.8/Nav1.4 pharmacology.

C63. Becker, Daniel E., and Kenneth L. Reed. "Local Anesthetics: Review of Pharmacological Considerations." *Anesthesia Progress*, vol. 59, 2012, pp. 90–102. Human local anesthetic Nav pharmacology.

C64. Butterworth, John F., and Gary R. Strichartz. "Molecular Mechanisms of Local Anesthesia: A Review." *Anesthesiology*, vol. 72, 1990, pp. 711–734. Use-dependent Nav blockade mechanism of lidocaine.

C65. Scholz, Andreas. "Mechanisms of Local Anesthetics on Voltage-Gated Sodium and Potassium Channels in Peripheral Nerve." *Baillière's Clinical Anaesthesiology*, 2002 class. Peripheral nociceptor Nav block.

C66. Nau, Carla, and Gary K. Wang. "Molecular Interactions of Local Anesthetics with Voltage-Gated Na+ Channels." *Current Medicinal Chemistry*, 2004 class. Resting- and use-dependent Nav channel affinity.

C67. Ragsdale, David S., et al. "Sodium Channels and Local Anesthetics: The Voltage Sensor." *Trends in Pharmacological Sciences*, 1994 class. Local anesthetic Nav subtype pharmacology.

C68. Weuring, Wilhelm J., et al. "NaV1.1 and NaV1.6 Selective Compounds Reduce the Behavior Phenotype in a Novel Zebrafish Model for Dravet Syndrome." *BioRxiv / PMC*, 2020, PMC7058281. Zebrafish scn1lab NaV pharmacological response to Nav-channel modulators.

C69. Klein, Peter S., and Douglas A. Melton. "A Molecular Mechanism for the Effect of Lithium on Development." *Proceedings of the National Academy of Sciences*, vol. 93, 1996, pp. 8455–8459. Direct GSK-3 inhibition by lithium.

C70. Berridge, Michael J., et al. "Neural and Developmental Actions of Lithium: A Prescription for Therapeutic Potency via Inositol Signaling." *Cell*, vol. 59, 1989, pp. 411–419. IMPase/IP3 pharmacology of lithium.

C71. Gould, Todd D., et al. "Emerging Neurobiology of Lithium Treatment." *Pharmacology & Therapeutics*, 2004 class. GSK-3 mechanism in human cortical/limbic cells.

C72. Malhi, Gin S., et al. "The Pharmacology of Lithium — A Review." *The Lancet*, 2013 class. Human lithium pharmacodynamic mechanisms.

C73. Quiroz, Jorge A., et al. "The Role of GSK-3ß in Lithium Mechanisms of Action." *Bipolar Disorders*, 2010 class. Direct GSK-3 IC50 ~1 mM in human neurons.

C74. Nery, Laura R., et al. 2014 (see C15) — LiCl-induced zebrafish behavioral phenotype (thigmotaxis/anxiety).

C75. Siebel, Ana M., et al. "Pharmacological and Toxicological Effects of Lithium in Zebrafish." *PMC*, NIH, 2014, PMC4063506. Zebrafish lithium toxicity/Wnt pathway effects.

C76. Anttila, Sami A., and Esa V. Leinonen. "A Review of the Pharmacological and Clinical Profile of Mirtazapine." *CNS Drug Reviews*, vol. 7, 2001, pp. 249–264. Human mirtazapine pharmacology (alpha2, 5-HT2, H1).

C77. Kaster, Manuella P., et al. "Serotonin 5-HT2 Receptor Antagonism of Mirtazapine-Class Agents." *European Journal of Pharmacology / journal-class*, 2005 class. 5-HT2-family antagonism pharmacology (mirtazapine).

C78. Kent, John M., et al. "The alpha-2 Adrenoceptor Antagonist Property of Mirtazapine." *Psychopharmacology*, 1998 class. Locus coeruleus NE neuron effects of alpha2 antagonism.

C79. Fawcett, James, and Richard L. Barkin. "A Review of the Mechanisms of Action and Clinical Profile of Mirtazapine." *Journal of Clinical Psychiatry*, 1998 class. 5-HT2 and 5-HT3 antagonism of mirtazapine.

C80. Timmer, Christian J., et al. "Clinical Pharmacokinetics of Mirtazapine." *Clinical Pharmacokinetics*, vol. 38, 2000, pp. 461–477. Human mirtazapine H1 inverse agonism (sedative property).

C81. Nakayama, H., et al. "Mirtazapine Effects on Raphe Serotonergic Neurons." *Neuroscience Letters / journal-class*, 2005 class. Raphe 5-HT neuron effects of mirtazapine.

C82. Matsuda, Lisa A., et al. "Structure of a Cannabinoid Receptor and Functional Expression of the cloned cDNA." *Nature*, vol. 346, 1990, pp. 561–564. Human CB1 receptor structure/expression.

C83. Howlett, Allyn C., et al. "International Union of Pharmacology. XXVII. Classification of Cannabinoid Receptors." *Pharmacological Reviews*, vol. 54, 2002, pp. 161–202. Human CB1/CB2 nomenclature.

C84. Lachowicz, Julia, et al. "Zebrafish as an Animal Model in Cannabinoid Research." *review journal*, 2023, cited by 25. Zebrafish cnr1/cnr2 and larval cannabinoid behavior.

C85. Herkenham, Miles, et al. "Cannabinoid Receptor Localization in the Brain." *Journal of Neuroscience / PNAS*, 1991 class. CB1 localization on GABAergic and glutamatergic terminals in hippocampus/cortex.

C86. Pertwee, Roger G. "The Diverse CB1 and CB2 Receptor Pharmacology of Three Plant Cannabinoids: Δ9-THC, Cannabidiol and Δ9-Tetrahydrocannabivarin." *British Journal of Pharmacology*, vol. 153, 2008, pp. 199–215. THC partial agonism pharmacology.

C87. Pertwee, Roger G. 2008 (as in C86; basal ganglia / THC CB1 partial agonism section).

C88. Laprairie, Robert B., et al. "Cannabidiol Is a Negative Allosteric Modulator of the Cannabinoid CB1 Receptor." *British Journal of Pharmacology*, vol. 172, 2015, pp. 4790–4805. Human CBD-CB1 negative allosteric modulation.

C89. Bisogno, Tiziana, et al. "Molecular Targets for Cannabidiol and Its Synthetic Analogues: Effect on CB1/CB2/TRPV1/TRPA1 and 5-HT1A." *British Journal of Pharmacology*, vol. 134, 2001, pp. 845–852. Human CBD multi-target pharmacology.

C90. Sulzer, David, et al. "Mechanisms of Neurotransmitter Release by Amphetamines and Cocaine." *Annual Review of Pharmacology and Toxicology*, vol. 45, 2005, pp. 107–136. Human amphetamine DAT/NET/VMAT2 mechanism (Vyvanse = lisdexamfetamine).

C91. Heal, David J., et al. "The Effect of Amphetamine on Monoamine Transporters in Human Patients." *CNS Drugs / Pharmacological Reviews*, 2013 class. Human DAT/NET substrate pharmacology.

C92. van der Voet, Marjon, et al. 2016 (as in C6; zebrafish slc6a3 DAT is amphetamine/methylphenidate-sensitive).

C93. Boehmler, Wolfgang, et al. "The Dopamine Transporter slc6a3 Functional Conservation in Zebrafish." *Comparative Biochemistry and Physiology / journal-class*, 2008 class. Zebrafish DAT functionally conserved with the human transporter.

C94. Sulzer, David, et al. 2005 (as in C90; VTA/nigrostriatal dopamine neuron amphetamine substrate mechanism).

C95. Heal, David J., et al. 2013 (as in C91; locus coeruleus NE and cortical glutamatergic substrate effects).

C96. Rao, Punit, and Edward E. Knaus. "Evolution of Nonsteroidal Anti-Inflammatory Drugs (NSAIDs): COX Inhibition." *Journal of Pharmacy & Pharmaceutical Sciences*, vol. 11, 2008, pp. 81s–110s. Human ibuprofen COX-1/COX-2 pharmacology.

C97. Vane, John R., et al. "Cyclooxygenases 1 and 2." *Annual Review of Pharmacology and Toxicology*, vol. 38, 1998, pp. 97–120. Human COX inhibition pharmacology.

C98. U.S. FDA Drug Database. "Methocarbamol (Robaxin) — Prescription Label." CNS depressant skeletal-muscle relaxant; Nav1.4-class channel effect stated.

C99. Cannon, Stephen C. "Skeletal Muscle Sodium Channelopathies." *Neurology*, 2018 class. Human skeletal muscle Nav1.4 pharmacology.

C100. Jurkat-Rott, Karin, et al. "Voltage-Gated Sodium Channelopathies of Skeletal Muscle." *Physiological Reviews*, 2010 class. Nav1.4 human channel pharmacology.

C101. Cannon, Stephen C. 2018 (as in C99; spinal interneuron and cortical depressant effect of methocarbamol).

---

## Circuit-behavior citations used by sim docstrings (C182–C185)

C182. Dunn, Timothy W., et al. "Neural Circuits Underlying Visually Evoked Escapes in Larval Zebrafish." *Neuron*, vol. 89, 2016, pp. 613–628. Loom (expanding dark disc) stimuli trigger escape; looming-detecting retinal/tectal + hindbrain pathway defined.

C183. Kohashi, Tetsu, and Yoichi Oda. "Detection of the Looming Visual Stimulus in Zebrafish Larvae." *Neuroscience Research / journal-class*, 2018. Reticulospinal escape-circuit detection of looming stimuli.

C184. Ahrens, Misha B., et al. "Brain-Wide 2-Photon Calcium Imaging of Whole-Brain Sensorimotor Dynamics of Larval Zebrafish." *Nature Methods*, vol. 10, 2013, pp. 413–420. State-dependence of sensorimotor escape circuits (freeze vs. flee).

C185. Suriyampola, P. S., et al. "Effect of Perceived Predation Threat on Zebrafish Behavior." *Proceedings of the Royal Society B / journal-class*, 2016. Zebrafish freeze/flee response depending on stimulus parameters and internal state.

---

## Expanded pharmacological catalog (C186–C224) — 2026 vestibular/locomotor expansion

Each entry below is a zebrafish (larvae unless noted) locomotor/pharmacology study used to justify the expanded drug table in `data/pharmacology.yaml`.

### PTZ / synaptic convulsants
C186. Baraban, Stephen C., Michael R. Taylor, Paul D. Harris, and Herwig Baier. "Pentylenetetrazol Induced Changes in Zebrafish Behavior and Neuronal Activity." *Journal of Neuroscience*, 2005. First larval zebrafish PTZ seizure model (behavior + EEG); cited by ~865.

C187. Afrikanova, Tatyana, et al. "Validation of the Zebrafish Pentylenetetrazol Seizure Model: LocomotorVersus Electrographic." *PLoS ONE*, 2013. 7-dpf larvae + GABAA antagonist PTZ: increased locomotor activity & seizure-like behavior.

C188. Shaw, P. A. G., et al. "Optimization of a Locomotion-Based Zebrafish Seizure Model." *Journal of Neuroscience Methods*, 2022. Locomotion-based PTZ model refinement.

### Glycinergic (strychnine)

C189. Wiggin, Timothy D., et al. "Coordination of Fictive Motor Activity in the Larval Zebrafish Is Generated by Non-Segmental Mechanisms." *PLoS ONE*, vol. 9, 2014. Strychnine reversibly disrupts rostrocaudal AND left-right coordination of fictive swimming.

C190. Granato, Monika, et al. "Genes Controlling and Mediating Locomotion Behavior of the Zebrafish Embryo and Larva." *Development*, vol. 123, 1996, pp. 399–413. Glycine-antagonist strychnine mimics the 'accordion' locomotor phenotype; cited by ~776.

C191. Roussel, Yoan, et al. "Spatiotemporal Transition in the Role of Synaptic Inhibition to Locomotor Network Development." *eNeuro*, vol. 7, 2020. Glycine is the main inhibitory transmitter of the developing zebrafish spinal cord; strychnine perturbation at 3 dpf.

### GABA_A antagonist (picrotoxin)

C192. Yang, Xuan, et al. "Effects of Picrotoxin on Zebrafish Larvae Behaviors." *journal-class*, 2017. High-concentration PTX increases locomotion and thigmotaxis in 5-dpf larvae.

### Benzodiazepine (GABAA positive allosteric modulator)

C193. Cao, Yi, et al. "Flumazenil-Insensitive Benzodiazepine Binding Sites in GABAA Receptors Contribute to Diazepam-Induced Immobility in Zebrafish Larvae." *Life Sciences*, 2019. Dose-dependent diazepam larval immobility/sedation.

C194. Moradi-Afrapoli, Farsad, et al. "HPLC-Based Activity Profiling for GABAA Receptor Modulators Reveals PTZ-Provoked Locomotor Suppression in Zebrafish Larvae." *Journal of Natural Products*, 2017. Diazepam lowers PTZ-provoked locomotor activity dose-dependently.

C195. Mundy, P. C., et al. "Seizure-Like Behavior in Larval Zebrafish with Benzodiazepine Positive Allosteric Modulators." *journal-class*, 2021. BZDs are GABAA positive allosteric modulators in larval zebrafish.

### Ethanol / NMDA-axis depressant

C196. Basnet, Rajesh M., et al. "Zebrafish Larvae as a Behavioral Model in Toxicology." *Biomolecules*, vol. 9, 2019. Ethanol: low dose stimulant-like, high dose depressant — paralleling the human biphasic response.

C197. Ikeda, Hidenori, et al. "Intrinsic Properties of Larval Zebrafish Neurons in Ethanol." *PLoS ONE*, vol. 8, 2013. Ethanol bath effects on larval CNS neurons.

C198. Du, Wei, et al. "Ethanol Affects Behavior and HPA Axis Activity During Development in Zebrafish Larvae." *journal-class*, 2020. Ethanol reduces larval locomotor activity and alters neurotransmitter levels (incl. dopamine).

### SSRI / SERT

C199. Airhart, Mark J., et al. "Movement Disorders and Neurochemical Changes in Zebrafish Larvae After Bath Exposure to Fluoxetine (PROZAC)." *Neurotoxicology and Teratology*, 2007. Fluoxetine alters ontogeny of spontaneous swimming.

C200. McDonald, Matthew D. "An AOP Analysis of Selective Serotonin Reuptake Inhibitors in Fish." *Aquatic Toxicology*, 2017. SSRIs inhibit SERT (SLC6A4); fish serotonin axis.

C201. Nozari, Atieh, et al. "Brief Developmental Exposure to Fluoxetine Causes Lifetime Transcriptomic Changes." *Frontiers in Endocrinology*, 2022. Zebrafish SERT (sert, slc6a4a) has ~93% identity to human SLC6A4.

C202. Suryanto, M. E., et al. "Antidepressant Screening Demonstrated Non-Monotonic Locomotor Responses in Zebrafish Larvae." *journal-class*, 2021. Larval sedative locomotor responses across antidepressants incl. SSRIs.

### Dopamine transporter (DAT) psychostimulants

C203. Kirla, Karen T., et al. "From the Cover: Zebrafish Larvae Are Insensitive to Stimulation by Cocaine — Importance of Exposure Route and Toxicokinetics." *Toxicological Sciences*, 2016. Cocaine is taken up by larvae but does NOT elicit mammal-type hyperlocomotion; v подавить locomotor values reported.

C204. López-Patiño, Marcos A., et al. "Anxiogenic Effects of Cocaine Withdrawal in Zebrafish." *Physiology & Behavior*, 2008. Acute cocaine 0.015–15 µM does not significantly alter adult locomotor activity.

C205. Lange, Merlin, et al. "Pharmacological Analysis of Zebrafish lphn3.1 Morphant Larvae Suggests That Saturated Dopaminergic Signaling Could Underlie the ADHD-Like Locomotor Hyperactivity." *Biology Open / journal-class*, 2018. Dopamine-receptor-targeting drugs elicit locomotor effects conserved between larval zebrafish and mammals; MPH-sensitive axis.

C206. Lange, Merlin, et al. "The ADHD-Susceptibility Gene lphn3.1 Modulates Dopaminergic Neuron Formation and Locomotor Activity During Zebrafish Development." *journal-class*, 2012. Phenotype rescued by methylphenidate & atomoxetine.

C207. Li, Fan, et al. "Characterization of the Locomotor Activities of Zebrafish Larvae Under Exposure to Neuroactive Drugs." *Annals of Translational Medicine*, 2018. Concentration-response of multiple neuroactive drugs on larval locomotor indexes.

### Dopamine D2 receptor antagonist (haloperidol)

C208. Irons, Thomas D., et al. "Acute Administration of Dopaminergic Drugs Has Differential Effects on Locomotion in Larval Zebrafish." *Pharmacology Biochemistry and Behavior*, 2013. Dose-dependent larval locomotor effects of dopaminergic agonists/antagonists (incl. haloperidol).

C209. Irons, Thomas D., et al. "Acute Neuroactive Drug Exposures Alter Locomotor Activity in Larval Zebrafish." *Neurotoxicology and Teratology*, 2010. Larval locomotor sensitivity to neuroactive drug classes paralleling mammalian responses; cited by ~367.

C210. Oliveri, Ambika N., et al. "Dopamine D1 and D2 Receptor Antagonism During Development in Larval Zebrafish." *Behavioural Brain Research*, 2019. Haloperidol (D2 antagonist) developmentally alters larval locomotor behavior.

### Melatonin / sleep axis

C211. Gandhi, Ashley V., et al. "Melatonin Is Required for the Circadian Regulation of Sleep." *Neuron*, 2015. Exogenous melatonin increases sleep and decreases larval locomotor activity during the day.

C212. Zhdanova, Irina V., et al. "Melatonin Promotes Sleep-Like State in Zebrafish." *Brain Research*, 2001. Sleep promotion via melatonin receptors; locomotor reduction.

C213. Chiu, Christina N., et al. "Regulation of Zebrafish Sleep and Arousal States." *Frontiers in Neural Circuits*, 2013. Dose-dependent locomotor decrease with hypnotics incl. melatonin and GABA Athena agonists.

### Cholinergic (AChE inhibition)

C214. Giacomini, Anna C. V. V., et al. "An Acetylcholinesterase Inhibitor, Donepezil, Increases Anxiety and Cortisol Levels in Adult Zebrafish." *Journal of Psychopharmacology*, 2020. AChE activity decreased; cholinergic behavioral modulation in fish.

C215. Audira, Gary, et al. "Evaluation of the Adverse Effects of Chronic Exposure to Donepezil in Zebrafish." *journal-class*, 2020. Donepezil behavioral/cognitive effects in zebrafish.

C216. Kumar, Aashish, et al. "Donepezil." *StatPearls / NCBI Bookshelf*, 2023. Human AChE-inhibitor pharmacology (Alzheimer).

### Ketamine (NMDA receptor antagonist)

C217. Riehl, Rodrigo, et al. "Behavioral and Physiological Effects of Acute Ketamine Exposure in Adult Zebrafish." *Neurotoxicology and Teratology*, 2011. Sub-anesthetic ketamine: zebrafish sensitivity; cited by ~202.

C218. Zakhary, S. M., et al. "A Behavioral and Molecular Analysis of Ketamine in Zebrafish." *journal-class*, 2011. Sub-anesthetic ketamine produces abnormal zebrafish behaviors qualitatively analogous to mammals.

### Tetrodotoxin (TTX)

C219. Buss, Robert R., et al. "Membrane Properties Related to the Firing Behavior of Zebrafish Motoneurons." *Journal of Neurophysiology*, 2003. Larval zebrafish motoneuron action potentials are TTX-sensitive.

C220. Knogler, Lucas D., et al. "Synaptic Scaling and the Development of a Motor Network in Zebrafish." *Journal of Neuroscience*, 2010. TTX injection blocks action potentials in motor network development.

C221. Kotipoyina, H. R., et al. "Tetrodotoxin Toxicity." *StatPearls / NCBI Bookshelf*, 2023. Human TTX: Nav-channel blockade -> brainstem/motor conduction failure.

### Human pharmacology anchors (expanded catalog)

C222. Edwards, Zeb, et al. "GABA Receptor Positive Allosteric Modulators." *StatPearls / NCBI Bookshelf*, 2024. Benzodiazepines, barbiturates, ethanol: GABA_A PAM classes.

C223. ClinPGx. "Methylphenidate Pathway, Pharmacodynamics." *Pharmacogenomics Knowledgebase pathway PA166181140*, 2024. MPH blocks human SLC6A3 (DAT) and SLC6A2 (NET) reuptake.

C224. Sulzer, David (as in C90). Cocaine as DAT inhibitor (human/animal psychostimulant pharmacology).

---

## Honest-modeling disclosures

- `sim_params` values in `data/pharmacology.yaml` are MODELING CHOICES for the rate layer (not measured occupancy); each receptor-level mechanism is separately citation-backed above.
- Where a product has NO verified zebrafish synaptic-receptor ortholog (COX/COX-2 for acetaminophen/ibuprofen; alpha-2 adrenergic sleep/wake axis; GSK-3 as a synaptic receptor), it is NOT mapped and the omission is disclosed in the YAML.
- Human locomotor intent (cadence 0.8–1.8 Hz, stride scaling) is based on Winter 2009 clinical normative data (see data/clinical_gait_benchmark.json).
