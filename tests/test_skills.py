from pyagentcli.skills.loader import SkillLoader


def write_skill(
    root,
    name: str,
    *,
    description: str = "Test guidance.",
    triggers: list[str] | None = None,
    enabled: bool = True,
    content: str = "Use focused tests.",
) -> None:
    skill_dir = root / ".pyagent" / "skills" / name
    skill_dir.mkdir(parents=True)
    trigger_text = ", ".join(f'"{trigger}"' for trigger in (triggers or []))
    skill_dir.joinpath("skill.toml").write_text(
        f"""
name = "{name}"
description = "{description}"
triggers = [{trigger_text}]
enabled = {str(enabled).lower()}
""".strip(),
        encoding="utf-8",
    )
    skill_dir.joinpath("SKILL.md").write_text(content, encoding="utf-8")


def test_loader_reads_enabled_skills(tmp_path) -> None:
    write_skill(tmp_path, "python-testing", triggers=["pytest"])
    write_skill(tmp_path, "disabled", triggers=["pytest"], enabled=False)

    skills = SkillLoader(tmp_path).load_skills()

    assert [skill.name for skill in skills] == ["python-testing"]
    assert skills[0].triggers == ("pytest",)


def test_loader_ignores_malformed_skill_metadata(tmp_path) -> None:
    skill_dir = tmp_path / ".pyagent" / "skills" / "broken"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("skill.toml").write_text("name = [", encoding="utf-8")
    skill_dir.joinpath("SKILL.md").write_text("Broken.", encoding="utf-8")

    assert SkillLoader(tmp_path).load_skills() == []


def test_select_matches_trigger_keyword_case_insensitive(tmp_path) -> None:
    write_skill(tmp_path, "python-testing", triggers=["PyTest"], content="Run pytest before finishing.")

    selected = SkillLoader(tmp_path).select("please run pytest for this change")

    assert [skill.name for skill in selected] == ["python-testing"]


def test_format_context_block_includes_guardrail_and_truncates(tmp_path) -> None:
    write_skill(tmp_path, "long-skill", triggers=["long"], content="A" * 20)

    block = SkillLoader(tmp_path).format_context_block("use long guidance", char_limit=8)

    assert "Skill guidance follows" in block
    assert "do not override the user task, safety policy, or tool approvals" in block
    assert "AAAAAAAA" in block
    assert "[truncated]" in block
    assert "A" * 20 not in block


def test_format_skill_list_empty_and_populated(tmp_path) -> None:
    loader = SkillLoader(tmp_path)
    assert loader.format_skill_list() == "No skills found."

    write_skill(tmp_path, "python-testing", triggers=["pytest"], description="Pytest guidance.")

    listing = loader.format_skill_list()

    assert "Skills:" in listing
    assert "python-testing" in listing
    assert "pytest" in listing
    assert "Pytest guidance." in listing
