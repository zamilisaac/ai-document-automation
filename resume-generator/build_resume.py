"""ATS-friendly resume generator.

Reads resume content from a JSON file and builds two PDFs:
  - an ATS version (single column, no photo, no tables) for online applications
  - a designed version with an optional photo for printing or emailing

Usage:
    python build_resume.py sample_resume.json
    python build_resume.py my_resume.json --photo photo.jpg
"""
import argparse
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, HRFlowable, KeepTogether)

PHOTO = None
F, FB = "Times-Roman", "Times-Bold"

name_st = ParagraphStyle("name", fontName=FB, fontSize=22, leading=26)
role_st = ParagraphStyle("role", fontName=F, fontSize=12.5, leading=16)
contact_st = ParagraphStyle("contact", fontName=F, fontSize=10.5, leading=15)
head_st = ParagraphStyle("head", fontName=FB, fontSize=12, leading=14, spaceBefore=5, spaceAfter=2)
body_st = ParagraphStyle("body", fontName=F, fontSize=10.5, leading=13.5, alignment=4)
job_st = ParagraphStyle("job", fontName=FB, fontSize=11, leading=14, spaceBefore=5, spaceAfter=1)
bullet_st = ParagraphStyle("bullet", fontName=F, fontSize=10.5, leading=12.9, leftIndent=16, bulletIndent=6)
small_st = ParagraphStyle("small", fontName=F, fontSize=10.5, leading=13.5, leftIndent=6)

# ------------------------------------------------------------------ content (filled from JSON)
NAME = TITLE = SUMMARY = ""
CONTACT, SKILLS, EXPERIENCE, PROJECTS, EDUCATION, CERTS, REFERENCES = [], [], [], [], [], [], []


def load(path):
    global NAME, TITLE, CONTACT, SUMMARY, SKILLS, EXPERIENCE, PROJECTS, EDUCATION, CERTS, REFERENCES
    d = json.load(open(path, encoding="utf-8"))
    NAME, TITLE, CONTACT, SUMMARY = d["name"], d["title"], d["contact"], d["summary"]
    SKILLS = [tuple(x) for x in d["skills"]]
    EXPERIENCE = [(e["role"], e["org"], e["dates"], e["bullets"]) for e in d["experience"]]
    PROJECTS = [(p["name"], p["org"], p["dates"], p["bullets"]) for p in d.get("projects", [])]
    EDUCATION = [(e["degree"], e["school"], e["year"], e.get("coursework")) for e in d["education"]]
    CERTS = [tuple(x) for x in d.get("certifications", [])]
    REFERENCES = [tuple(x) for x in d.get("references", [])]


# ------------------------------------------------------------------ layout
def rule():
    return HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=4, spaceAfter=2)


def section(title):
    return [rule(), Paragraph(title.upper(), head_st)]


def bullets(items):
    return [Paragraph(t, bullet_st, bulletText="•") for t in items]


def entry(title, org, dates, items):
    hdr = Paragraph(f"<i>{title}</i>, <b>{org}</b> (<b>{dates}</b>)", job_st)
    return [KeepTogether([hdr] + bullets(items[:2]))] + bullets(items[2:])


def build(out, ats):
    story = []
    if ats:
        c = lambda st: ParagraphStyle(st.name + "c", parent=st, alignment=1)
        story += [Paragraph(NAME.upper(), c(name_st)),
                  Paragraph(TITLE, c(role_st)), Spacer(1, 3),
                  Paragraph(" | ".join(CONTACT), c(contact_st)), Spacer(1, 2)]
    else:
        photo = Table([[Image(PHOTO, width=30 * mm, height=38 * mm)]],
                      colWidths=[31.5 * mm], rowHeights=[39.5 * mm])
        photo.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.6, colors.black),
                                   ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                   ("VALIGN", (0, 0), (-1, -1), "MIDDLE")] +
                                  [(p, (0, 0), (-1, -1), 0) for p in
                                   ("LEFTPADDING", "RIGHTPADDING", "TOPPADDING", "BOTTOMPADDING")]))
        block = [Paragraph(NAME.upper(), name_st), Paragraph(TITLE.upper(), role_st),
                 HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=6, spaceAfter=6),
                 Paragraph(f"<b>Phone:</b> {CONTACT[1]} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Email:</b> {CONTACT[2]}", contact_st),
                 Paragraph(f"<b>Location:</b> {CONTACT[0]}", contact_st)]
        hdr = Table([[photo, block]], colWidths=[35 * mm, None])
        hdr.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("LEFTPADDING", (1, 0), (1, 0), 8)]))
        story += [hdr, Spacer(1, 4)]

    story += section("Summary" if ats else "Professional Summary") + [Paragraph(SUMMARY, body_st)]
    story += section("Skills" if ats else "Core Competencies")
    story += [Paragraph(f"<b>{k}:</b> {v}", small_st) for k, v in SKILLS]

    story += section("Experience" if ats else "Professional Experience")
    for e in EXPERIENCE:
        story += entry(*e)

    if PROJECTS:
        first, *rest = PROJECTS
        story.append(KeepTogether(section("Projects") + entry(*first)))
        for p in rest:
            story += entry(*p)

    edu = section("Education")
    for deg, school, yr, cw in EDUCATION:
        edu.append(Paragraph(f"<b>{deg}</b>, {school} ({yr})", job_st))
        if cw:
            edu.append(Paragraph(f"<b>Relevant Coursework:</b> {cw}", small_st))
    story.append(KeepTogether(edu))

    story.append(KeepTogether(section("Certifications") +
                              bullets([f"<b>{n}</b>, {s}" for n, s in CERTS])))

    if not REFERENCES:
        refs = [Paragraph("Available upon request.", small_st)]
    elif ats:
        refs = bullets([f"<b>{n}</b>, {t}, {o} | {ph}" for n, t, o, ph in REFERENCES])
    else:
        ref_st = ParagraphStyle("ref", parent=small_st)
        t = Table([[Paragraph(f"<b>{n}</b><br/><b>{ti}</b><br/>{o}<br/>{ph}", ref_st)
                    for n, ti, o, ph in REFERENCES]], colWidths=["50%", "50%"])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        refs = [t]
    story.append(KeepTogether(section("References") + refs))

    SimpleDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=13 * mm, bottomMargin=11 * mm,
                      title=f"{NAME} - Resume", author=NAME,
                      subject=TITLE).build(story)
    print("ok", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build ATS and designed resume PDFs from JSON.")
    ap.add_argument("data", help="resume content as JSON")
    ap.add_argument("--photo", help="optional photo for the designed version")
    ap.add_argument("--out", default="output", help="output folder")
    a = ap.parse_args()
    load(a.data)
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.join(a.out, NAME.replace(" ", "_"))
    build(stem + "_Resume_ATS.pdf", ats=True)
    if a.photo:
        PHOTO = a.photo
        build(stem + "_Resume.pdf", ats=False)
