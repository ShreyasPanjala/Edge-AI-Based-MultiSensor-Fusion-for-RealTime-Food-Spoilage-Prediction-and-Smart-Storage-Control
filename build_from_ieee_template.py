"""Generate fully formatted IEEE conference document directly using conference-template-a4.docx."""

import io
import re
import zipfile
from pathlib import Path
import docx
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

TEMPLATE_PATH = Path("conference-template-a4.docx")
OUTPUT_PATH = Path("IEEE_Conference_Paper.docx")
ALT_OUTPUT_PATH = Path("conference_paper_ieee.docx")


def prepare_template():
    """Normalize the PURL namespaces in the original IEEE template so python-docx can manipulate it."""
    replacements = {
        b'http://purl.oclc.org/ooxml/wordprocessingml/main': b'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        b'http://purl.oclc.org/ooxml/officeDocument/relationships': b'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        b'http://purl.oclc.org/ooxml/drawingml/main': b'http://schemas.openxmlformats.org/drawingml/2006/main',
        b'http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing': b'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        b'http://purl.oclc.org/ooxml/officeDocument/math': b'http://schemas.openxmlformats.org/officeDocument/2006/math',
        b'http://purl.oclc.org/ooxml/officeDocument/extendedProperties': b'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
        b'http://purl.oclc.org/ooxml/officeDocument/docPropsVTypes': b'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes',
        b'http://purl.oclc.org/ooxml/officeDocument/customXml': b'http://schemas.openxmlformats.org/officeDocument/2006/customXml',
    }
    with open(TEMPLATE_PATH, "rb") as f:
        in_bytes = f.read()

    in_zip = zipfile.ZipFile(io.BytesIO(in_bytes))
    out_buf = io.BytesIO()
    out_zip = zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED)

    for item in in_zip.infolist():
        content = in_zip.read(item.filename)
        for old, new in replacements.items():
            content = content.replace(old, new)
        out_zip.writestr(item, content)

    out_zip.close()
    return io.BytesIO(out_buf.getvalue())


def create_omml_eq1():
    return parse_xml(
        f'<m:oMath {nsdecls("m")}>\n'
        f'  <m:sSub><m:e><m:r><m:t>O</m:t></m:r></m:e><m:sub><m:r><m:t>2 (gas)</m:t></m:r></m:sub></m:sSub>\n'
        f'  <m:r><m:t> + 2</m:t></m:r>\n'
        f'  <m:sSup><m:e><m:r><m:t>e</m:t></m:r></m:e><m:sup><m:r><m:t>-</m:t></m:r></m:sup></m:sSup>\n'
        f'  <m:r><m:t> ⟶ 2</m:t></m:r>\n'
        f'  <m:sSubSup><m:e><m:r><m:t>O</m:t></m:r></m:e><m:sub><m:r><m:t>(adsorbed)</m:t></m:r></m:sub><m:sup><m:r><m:t>-</m:t></m:r></m:sup></m:sSubSup>\n'
        f'</m:oMath>'
    )


def create_omml_eq2():
    return parse_xml(
        f'<m:oMath {nsdecls("m")}>\n'
        f'  <m:r><m:t>R + </m:t></m:r>\n'
        f'  <m:sSubSup><m:e><m:r><m:t>O</m:t></m:r></m:e><m:sub><m:r><m:t>(adsorbed)</m:t></m:r></m:sub><m:sup><m:r><m:t>-</m:t></m:r></m:sup></m:sSubSup>\n'
        f'  <m:r><m:t> ⟶ RO + </m:t></m:r>\n'
        f'  <m:sSup><m:e><m:r><m:t>e</m:t></m:r></m:e><m:sup><m:r><m:t>-</m:t></m:r></m:sup></m:sSup>\n'
        f'</m:oMath>'
    )


def create_omml_eq3():
    return parse_xml(
        f'<m:oMath {nsdecls("m")}>\n'
        f'  <m:sSub><m:e><m:r><m:t>V</m:t></m:r></m:e><m:sub><m:r><m:t>out</m:t></m:r></m:sub></m:sSub>\n'
        f'  <m:r><m:t> = </m:t></m:r>\n'
        f'  <m:sSub><m:e><m:r><m:t>V</m:t></m:r></m:e><m:sub><m:r><m:t>CC</m:t></m:r></m:sub></m:sSub>\n'
        f'  <m:r><m:t> · </m:t></m:r>\n'
        f'  <m:f>\n'
        f'    <m:num><m:sSub><m:e><m:r><m:t>R</m:t></m:r></m:e><m:sub><m:r><m:t>L</m:t></m:r></m:sub></m:sSub></m:num>\n'
        f'    <m:den><m:sSub><m:e><m:r><m:t>R</m:t></m:r></m:e><m:sub><m:r><m:t>s</m:t></m:r></m:sub></m:sSub><m:r><m:t> + </m:t></m:r><m:sSub><m:e><m:r><m:t>R</m:t></m:r></m:e><m:sub><m:r><m:t>L</m:t></m:r></m:sub></m:sSub></m:den>\n'
        f'  </m:f>\n'
        f'</m:oMath>'
    )


def generate_document():
    template_buf = prepare_template()
    doc = docx.Document(template_buf)

    # Clear out all existing paragraphs and tables from template body
    body_elm = doc._body._element
    # Keep the final sectPr so we have template's section properties
    final_sectPr = body_elm.xpath("./w:sectPr")
    final_sectPr_elem = final_sectPr[0] if final_sectPr else None

    # Remove all children of body except final sectPr
    for child in list(body_elm):
        if child.tag.endswith("sectPr"):
            continue
        body_elm.remove(child)

    # --- SECTION 1: Single Column Header (Title, Authors, Abstract, Keywords) ---
    s1 = doc.sections[0]
    # Keep A4 paper size and IEEE margins:
    s1.top_margin = Inches(0.75)
    s1.bottom_margin = Inches(1.0)
    s1.left_margin = Inches(0.62)
    s1.right_margin = Inches(0.62)
    s1.page_width = Inches(8.27)
    s1.page_height = Inches(11.69)

    # Configure Section 1 as single column (spanning full width)
    cols1 = s1._sectPr.xpath("./w:cols")
    if cols1:
        cols1[0].set(qn("w:num"), "1")
    else:
        c = parse_xml(f'<w:cols {nsdecls("w")} w:num="1" w:space="36pt"/>')
        s1._sectPr.append(c)

    # 1. Paper Title
    p_title = doc.add_paragraph(style="paper title")
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run(
        "A Zero-Allocation TinyML Stacking Hybrid Architecture for Real-Time Volatile Fruit Spoilage Detection on Edge Microcontrollers"
    )

    # 2. Authors Table (6 authors in 2 rows of 3 columns)
    auth_table = doc.add_table(rows=2, cols=3)
    auth_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    authors_data = [
        (0, 0, "1st Shreyas Panjala", "Dept. of Artificial Intelligence\nand Data Science", "Koneru Lakshmaiah Education Foundation", "Hyderabad, India", "panjalashreyas@klh.edu.in"),
        (0, 1, "2nd Ch. Karthikeya Sivarama Krishna", "Dept. of Artificial Intelligence\nand Data Science", "Koneru Lakshmaiah Education Foundation", "Hyderabad, India", "chkarthikeya@klh.edu.in"),
        (0, 2, "3rd Abhinav Chowdary Sunkara", "Dept. of Artificial Intelligence\nand Data Science", "Koneru Lakshmaiah Education Foundation", "Hyderabad, India", "abhinavchowdary@klh.edu.in"),
        (1, 0, "4th B. Vasudeva", "Dept. of Computer Science\nand Information Technology", "Koneru Lakshmaiah Education Foundation", "Hyderabad, India", "bellamkondavasudeva@klh.edu.in"),
        (1, 1, "5th T. Harsha Vardhan", "Dept. of Artificial Intelligence\nand Data Science", "Koneru Lakshmaiah Education Foundation", "Hyderabad, India", "t.harshavardhan@klh.edu.in"),
        (1, 2, "6th Kurakula Anudeep", "Dept. of Electronics and\nCommunication Engineering", "Koneru Lakshmaiah Education Foundation", "Hyderabad, India", "k.anudeep@klh.edu.in"),
    ]

    for row_idx in range(2):
        for col_idx in range(3):
            cell = auth_table.rows[row_idx].cells[col_idx]
            cell.width = Inches(2.34)
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>\n'
                f'  <w:top w:val="none"/>\n'
                f'  <w:left w:val="none"/>\n'
                f'  <w:bottom w:val="none"/>\n'
                f'  <w:right w:val="none"/>\n'
                f'</w:tcBorders>'
            )
            tcPr.append(tcBorders)

    for row_idx, col_idx, name, dept, org, loc, email in authors_data:
        cell = auth_table.rows[row_idx].cells[col_idx]
        p = cell.paragraphs[0]
        p.style = "Author"
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0

        r_name = p.add_run(f"{name}\n")
        r_name.font.name = "Times New Roman"
        r_name.font.size = Pt(10)
        r_name.bold = True

        r_dept = p.add_run(f"{dept}\n{org}\n")
        r_dept.font.name = "Times New Roman"
        r_dept.font.size = Pt(9)
        r_dept.italic = True

        r_loc = p.add_run(f"{loc}\n")
        r_loc.font.name = "Times New Roman"
        r_loc.font.size = Pt(9)

        r_mail = p.add_run(email)
        r_mail.font.name = "Times New Roman"
        r_mail.font.size = Pt(8.5)

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(0)
    p_sp.paragraph_format.space_after = Pt(6)

    # 3. Abstract (Spans full width at top)
    p_abs = doc.add_paragraph(style="Abstract")
    p_abs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_abs.paragraph_format.space_before = Pt(6)
    p_abs.paragraph_format.space_after = Pt(4)
    p_abs.paragraph_format.line_spacing = 1.0
    r_albl = p_abs.add_run("Abstract—")
    r_albl.font.name = "Times New Roman"
    r_albl.font.size = Pt(9)
    r_albl.bold = True
    r_albl.italic = True

    abs_text = (
        "Post-harvest food waste constitutes a critical global challenge, with approximately 30 to 40 percent of agricultural produce lost before consumption due to inadequate real-time spoilage tracking. Conventional quality assessment relying on destructive penetrometry or gas chromatography is labor-intensive, slow, and unsuitable for continuous supply chain monitoring. This paper introduces an autonomous, ultra-fast Edge-AI Electronic Nose (E-Nose) framework for non-destructive fruit freshness and spoilage classification deployed on resource-constrained edge microcontrollers. We present a multi-estimator Stacking Hybrid architecture combining shallow Random Forests, regularized Decision Trees, standardized Logistic Regression, and Gaussian Naive Bayes into an out-of-fold calibrated meta-classifier. Evaluated on a comprehensive benchmark of 69,110 time-series gas sensor observations, the proposed hybrid architecture achieves a peak holdout classification accuracy of 99.99 percent, a weighted F1-score of 0.9999, and zero false alarms (100.00 percent specificity) across 17,278 holdout test samples. Under a stringent 4-fold Leave-One-Day-Out (LODO) cross-validation protocol simulating unseen post-harvest days, the system achieves 95.81 percent pooled accuracy and an F1-score of 0.9580, demonstrating resilient cross-batch generalizability. Furthermore, the model accurately flags 85.26 percent of biological transition samples during the pre-symptomatic climacteric ripening peak prior to visible necrotic decay. To enable practical deployment, the continuous probability surface is compiled into a constant-time Flash-resident lookup representation. Real-hardware compiler verification confirms zero bytes of dynamic heap allocation, a sub-microsecond inference latency, 22.0 percent program Flash usage, and 100.00 percent exact numerical parity across all 4,096 discrete 12-bit ADC states."
    )
    r_atxt = p_abs.add_run(abs_text)
    r_atxt.font.name = "Times New Roman"
    r_atxt.font.size = Pt(9)
    r_atxt.bold = True

    # 4. Keywords (Spans full width at top)
    p_idx = doc.add_paragraph(style="Keywords")
    p_idx.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_idx.paragraph_format.space_before = Pt(0)
    p_idx.paragraph_format.space_after = Pt(12)
    p_idx.paragraph_format.line_spacing = 1.0
    r_ilbl = p_idx.add_run("Keywords—")
    r_ilbl.font.name = "Times New Roman"
    r_ilbl.font.size = Pt(9)
    r_ilbl.bold = True
    r_ilbl.italic = True

    r_itxt = p_idx.add_run("TinyML, Electronic Nose, Gas Transduction, Fruit Spoilage Detection, Stacking Classifier, Embedded Edge Computing.")
    r_itxt.font.name = "Times New Roman"
    r_itxt.font.size = Pt(9)

    # --- SECTION 2: Continuous Break, Strictly Two-Column Layout for Main Body ---
    s2 = doc.add_section(WD_SECTION_START.CONTINUOUS)
    s2.top_margin = Inches(0.75)
    s2.bottom_margin = Inches(1.0)
    s2.left_margin = Inches(0.63)
    s2.right_margin = Inches(0.63)
    s2.page_width = Inches(8.27)
    s2.page_height = Inches(11.69)

    # Configure Section 2 strictly as Two Columns with 18pt (0.25 in) spacing
    cols2 = s2._sectPr.xpath("./w:cols")
    if cols2:
        cols2[0].set(qn("w:num"), "2")
        cols2[0].set(qn("w:space"), "260")
        cols2[0].set(qn("w:equalWidth"), "1")
    else:
        c2 = parse_xml(f'<w:cols {nsdecls("w")} w:num="2" w:space="260" w:equalWidth="1"/>')
        s2._sectPr.append(c2)

    # Helper function to add body paragraphs
    def add_body(text, space_after=4):
        p = doc.add_paragraph(style="Body Text")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.first_line_indent = Inches(0.14)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        return p

    def add_heading1(text):
        p = doc.add_paragraph(style="Heading 1")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.font.small_caps = True
        r.bold = True
        return p

    def add_heading2(text):
        p = doc.add_paragraph(style="Heading 2")
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.italic = True
        return p

    def add_bullet(text):
        p = doc.add_paragraph(style="bullet list")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.left_indent = Inches(0.18)
        r_b = p.add_run("• ")
        r_b.font.name = "Times New Roman"
        r_b.font.size = Pt(9.5)
        r_b.bold = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(9.5)
        return p

    def add_equation_p(omml_fn, eq_num):
        p = doc.add_paragraph(style="equation")
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.add_run("\t")
        p._p.append(omml_fn())
        p.add_run(f"\t{eq_num}")
        return p

    def add_fig_placeholder(caption):
        # 1-cell table with 1 column width (3.42 in)
        t = doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.rows[0].cells[0]
        cell.width = Inches(3.42)
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>\n'
            f'  <w:top w:val="single" w:sz="6" w:color="A0A0A0"/>\n'
            f'  <w:left w:val="single" w:sz="6" w:color="A0A0A0"/>\n'
            f'  <w:bottom w:val="single" w:sz="6" w:color="A0A0A0"/>\n'
            f'  <w:right w:val="single" w:sz="6" w:color="A0A0A0"/>\n'
            f'</w:tcBorders>'
        )
        tcPr.append(borders)
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8F8F8"/>')
        tcPr.append(shd)

        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(36)
        cp.paragraph_format.space_after = Pt(36)
        cr = cp.add_run("[ System Architecture Diagram Placeholder ]")
        cr.font.name = "Times New Roman"
        cr.font.size = Pt(8.5)
        cr.font.color.rgb = RGBColor(120, 120, 120)
        cr.italic = True

        p_cap = doc.add_paragraph(style="figure caption")
        p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cap.paragraph_format.space_before = Pt(4)
        p_cap.paragraph_format.space_after = Pt(8)
        rc = p_cap.add_run(caption)
        rc.font.name = "Times New Roman"
        rc.font.size = Pt(8)
        rc.italic = True

    # --- SECTION I: INTRODUCTION ---
    add_heading1("I. INTRODUCTION")
    add_body(
        "Agricultural food security and supply chain sustainability are severely undermined by post-harvest loss. According to the Food and Agriculture Organization (FAO), over one-third of all perishable fruits and vegetables are discarded annually along post-harvest supply chains, cold storage facilities, and retail distribution centers [1]. Fresh fruit undergoes a continuous biochemical respiration process following harvest, leading to structural softening, moisture loss, and eventual microbiological decomposition."
    )
    add_body("Existing quality inspection approaches present fundamental trade-offs:")
    add_bullet("Destructive Mechanical Testing: Penetrometer firmness testing and soluble solids refractometry compromise produce integrity and only sample small fractions of a batch [2].")
    add_bullet("Laboratory Analytical Instrumentation: Gas Chromatography-Mass Spectrometry (GC-MS) provides exquisite chemical specificity but requires benchtop instrumentation, trained operators, and prohibitive analytical turnaround times [3].")
    add_bullet("Computer Vision & Optical Inspection: Machine vision systems assess surface pigmentation and fungal spots; however, visible surface discoloration represents a delayed, post-symptomatic indicator of decay that appears well after metabolic degradation has occurred [4].")
    add_body(
        "Non-destructive gas sensing through Electronic Noses (E-Noses) offers an attractive alternative. During post-harvest ripening and senescence, fruits release a dynamic spectrum of volatile organic compounds (VOCs)—including ethylene, ethanol, acetate esters, acetaldehyde, and carbon dioxide—which act as early biochemical signatures of shelf-life status [5]. However, traditional machine learning models for E-Noses typically require high-power microprocessors or cloud connectivity, introducing communication latency, privacy concerns, and network dependence [6]."
    )
    add_body(
        "Deploying intelligent classifiers directly onto low-power edge computing devices (TinyML) solves these constraints. Nonetheless, univariate and multi-sensor time-series on microcontrollers suffer from continuous sensor drift, baseline temperature dependence, and severe memory limitations. Standard embedded runtimes impose significant memory arena overhead and dynamic heap fragmentation risks."
    )
    add_body("To address these challenges, this paper presents a complete, zero-runtime TinyML system architecture for non-destructive fruit freshness assessment. The major contributions of this work are as follows:")
    add_bullet("Multi-Estimator Stacking Architecture: We develop an out-of-fold (OOF) cross-validated stacking meta-classifier uniting four diverse base learners that achieves 99.99% accuracy and an F1-score of 0.9999 on benchmark test partitions.")
    add_bullet("Rigorous Cross-Day Generalization Benchmark: We document the temporal leakage inherent in random time-series splits and establish a rigorous 4-fold Leave-One-Day-Out (LODO) validation benchmark, demonstrating that calibrated linear and thresholding models maintain 95.81% pooled accuracy across independent harvesting days.")
    add_bullet("Pre-Symptomatic Transition Phase Detection: We isolate the biological climacteric ripening peak (Day 3) from binary training, demonstrating that our architecture detects biochemical volatile surges 24 to 48 hours before physical decomposition.")
    add_bullet("Zero-Allocation Flash Compilation: We transpile the complete continuous probability surface into a constant-time Flash-resident lookup table over the entire 12-bit ADC space, achieving sub-microsecond latency, 0 bytes dynamic heap allocation, and 100.00% exact numerical parity.")

    # --- SECTION II: SYSTEM ARCHITECTURE & TRANSDUCTION PRINCIPLES ---
    add_heading1("II. SYSTEM ARCHITECTURE & TRANSDUCTION PRINCIPLES")
    add_fig_placeholder("Fig. 1. Overall architecture of the proposed system.")
    add_heading2("A. Metal-Oxide Semiconductor Gas Transduction")
    add_body(
        "The primary chemical transducer is a broad-spectrum metal-oxide semiconductor (MOS) gas sensor utilizing a heated tin dioxide sensing layer. In clean ambient air, oxygen molecules adsorb onto the polycrystalline grain boundaries of the surface, trapping conduction band electrons and forming an insulating depletion barrier:"
    )
    add_equation_p(create_omml_eq1, "(1)")
    add_body("When the sensor is exposed to reducing volatile organic compounds (R) emitted during fruit ripening:")
    add_equation_p(create_omml_eq2, "(2)")
    add_body(
        "The trapped electrons are released back into the conduction band, decreasing the sensor's surface resistance in proportion to the ambient VOC concentration [7]."
    )

    add_heading2("B. Signal Conditioning and Quantization")
    add_body("The sensor resistance is conditioned through a load resistor forming a voltage divider:")
    add_equation_p(create_omml_eq3, "(3)")
    add_body(
        "The analog potential is sampled via an on-chip 12-bit successive-approximation register Analog-to-Digital Converter operating over an input of 0 to 3.3V, producing integer levels from 0 to 4095."
    )

    add_heading2("C. Environmental Context Telemetry")
    add_body(
        "Ambient temperature and relative humidity alter the reaction kinetics of adsorbed oxygen ions on the sensor surface. An ambient digital sensor logs environmental telemetry concurrently. To prevent uncalibrated synthetic biases, environmental readings are captured for diagnostic telemetry and logging, while the primary machine learning feature space operates directly on calibrated gas transducer values."
    )

    # --- SECTION III: DATASET ARCHITECTURE & VOLATILE TRANSITION DYNAMICS ---
    add_heading1("III. DATASET ARCHITECTURE & VOLATILE TRANSITION DYNAMICS")
    add_heading2("A. Benchmark Ingestion and Multi-Fruit Applicability")
    add_body(
        "Empirical validation is performed on the open-access Food Freshness E-Nose Benchmark Dataset [8]. The dataset records continuous, high-frequency gas sensor time-series across progressive ripening cycles. While the primary baseline is benchmarked against continuous climacteric ripening series, the underlying gas-transduction framework is commodity-agnostic."
    )
    add_heading2("B. Protocol Formulation: Exclusion of Biological Transition")
    add_body("In the source benchmark, readings are acquired sequentially across five consecutive ripening days:")
    add_bullet("Day 1 and 2 (FRESH): 40,054 observations representing edible states.")
    add_bullet("Day 4 and 5 (SPOILED): 29,056 observations representing post-climacteric necrosis.")
    add_bullet("Day 3 (TRANSITION): 13,395 observations representing the climacteric ripening peak.")
    add_body(
        "Forcing an artificial binary boundary across Day 3 distorts the ground truth of clean physiological states. Therefore, Day 3 is excluded from primary training and reserved for an isolated transition phase analysis."
    )

    # --- SECTION IV: PROPOSED MULTI-ESTIMATOR STACKING HYBRID METHODOLOGY ---
    add_heading1("IV. PROPOSED MULTI-ESTIMATOR STACKING HYBRID METHODOLOGY")
    add_heading2("A. Base Estimator Suite")
    add_body("The base model suite combines complementary inductive biases:")
    add_bullet("Random Forest: An ensemble of 5 shallow decision trees trained via bootstrap aggregation to constrain variance.")
    add_bullet("Decision Tree: A cost-complexity regularized tree that creates deterministic orthogonal partitions.")
    add_bullet("Logistic Regression: A linear model with L2 weight regularization operating on standardized features.")
    add_bullet("Gaussian Naive Bayes: A maximum-likelihood generative estimator fitting class-conditional Gaussian distributions.")

    add_heading2("B. Out-of-Fold Stacking Meta-Learner")
    add_body(
        "Directly training a meta-learner on the training predictions of base estimators induces catastrophic overfitting. To prevent leakage, we implement a 5-fold Stratified Out-of-Fold cross-validation scheme. For each fold, continuous posterior probabilities are inferred on the held-out validation fifth. The resulting meta-feature matrix is used to fit a Logistic Regression meta-learner."
    )

    # --- SECTION V: EXPERIMENTAL RESULTS & BENCHMARK DISCUSSION ---
    add_heading1("V. EXPERIMENTAL RESULTS & BENCHMARK DISCUSSION")
    add_heading2("A. Peak Classification Performance")
    add_body(
        "Under a standard stratified holdout evaluation, the latest Stacking Hybrid Model achieves near-perfect classification performance. The overall accuracy is 99.99 percent, with a weighted precision and recall of 0.9999. The full confusion matrix on the 17,278 holdout samples demonstrates exactly zero false positives, guaranteeing that fresh produce is never erroneously flagged as spoiled."
    )
    add_heading2("B. Cross-Day Generalization Validation")
    add_body(
        "To rigorously test true cross-batch generalization, we conduct a 4-fold Leave-One-Day-Out cross-validation over independent harvesting days. Standardized Logistic Regression achieves 95.81 percent pooled accuracy across 69,110 out-of-fold samples. Unregularized non-linear trees drop significantly on held-out intermediate days due to missing threshold distributions."
    )

    # --- SECTION VI: ZERO-ALLOCATION TINYML TRANSPILATION & COMPILATION ---
    add_heading1("VI. ZERO-ALLOCATION TINYML TRANSPILATION & COMPILATION")
    add_body(
        "Because the sensor feature domain is quantized to 12-bit ADC integers, the entire continuous probability function can be precomputed into a constant-time Flash-resident lookup table. We verified the generated C++ header against the Python scikit-learn model across all 4,096 discrete ADC integers. Profiling confirmed sub-microsecond latency, 0 bytes dynamic heap allocation, and 22.0 percent program Flash storage usage."
    )

    # --- SECTION VII: CONCLUSION ---
    add_heading1("VII. CONCLUSION")
    add_body(
        "This paper presented a complete, ultra-fast, zero-allocation Edge-AI Electronic Nose framework for non-destructive fruit spoilage classification. Transpilation of the probability surface into a Flash-resident lookup table guarantees sub-microsecond latency, zero dynamic heap allocation, and 100 percent numerical parity on edge microcontrollers. The proposed system provides a practical, low-cost solution for automated post-harvest quality monitoring."
    )

    # --- REFERENCES ---
    p_ref_h = doc.add_paragraph(style="Heading 5")
    p_ref_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ref_h.paragraph_format.space_before = Pt(14)
    p_ref_h.paragraph_format.space_after = Pt(4)
    r_rh = p_ref_h.add_run("REFERENCES")
    r_rh.font.name = "Times New Roman"
    r_rh.font.size = Pt(10)
    r_rh.font.small_caps = True
    r_rh.bold = True

    references_list = [
        "[1] Food and Agriculture Organization of the United Nations (FAO), The State of Food and Agriculture: Moving forward on food loss and waste reduction, Rome, Italy: FAO, 2019.",
        '[2] B. M. Nicolaï et al., "Nondestructive measurement of fruit and vegetable quality by means of NIR spectroscopy: A review," Postharvest Biology and Technology, vol. 46, no. 2, pp. 99–118, 2007.',
        '[3] S. Grassi et al., "Advances in electronic nose technology for food quality inspection: A review," Sensors, vol. 22, no. 8, p. 2934, 2022.',
        '[4] J. Blasco et al., "Machine vision-based quality inspection of agricultural products," Computers and Electronics in Agriculture, vol. 182, p. 106012, 2021.',
        '[5] K. Arshak et al., "A review of gas sensors employed in electronic nose applications," Sensor Review, vol. 24, no. 2, pp. 181–198, 2004.',
        '[6] C. R. Banbury et al., "Benchmarking TinyML systems: Challenges and direction," IEEE Micro, vol. 41, no. 6, pp. 104–114, 2021.',
        '[7] N. Yamazoe, "Toward innovations of gas sensor technology," Sensors and Actuators B: Chemical, vol. 108, no. 1-2, pp. 2–14, 2005.',
        '[8] A. M. Dawoud, "Food Freshness E-Nose Benchmark Dataset," Kaggle Datasets, 2023.',
    ]

    for ref in references_list:
        p_ref = doc.add_paragraph(style="references")
        p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.paragraph_format.space_before = Pt(0)
        p_ref.paragraph_format.space_after = Pt(2)
        p_ref.paragraph_format.line_spacing = 1.0
        p_ref.paragraph_format.left_indent = Inches(0.25)
        p_ref.paragraph_format.first_line_indent = Inches(-0.25)
        r_ref = p_ref.add_run(ref)
        r_ref.font.name = "Times New Roman"
        r_ref.font.size = Pt(8)

    doc.save(OUTPUT_PATH)
    print(f"Successfully generated IEEE Word document: {OUTPUT_PATH.resolve()}")
    try:
        doc.save(ALT_OUTPUT_PATH)
        print(f"Also updated: {ALT_OUTPUT_PATH.resolve()}")
    except Exception as e:
        print(f"Note: {ALT_OUTPUT_PATH.name} is currently open in Word ({e}), so saved to {OUTPUT_PATH.name}")


if __name__ == "__main__":
    generate_document()
