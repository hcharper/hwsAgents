"""Tests for YAML loading, prompt construction, memory, and nested updates."""

import shutil
import tempfile
from pathlib import Path

from shared.data_manager import DataManager
from shared.memory import ChannelMemory
from pricing_agent.prompts import build_system_prompt as build_pricing_prompt
from manager_agent.prompts import build_system_prompt as build_manager_prompt
from manager_agent.handler import _set_nested


DATA_DIR = Path(__file__).parent.parent / "data"


class TestDataManager:
    def test_load_pricing(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        assert "products" in dm.pricing
        assert len(dm.pricing["products"]) > 0

    def test_load_objections(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        assert "universal" in dm.objections
        assert "per_product" in dm.objections
        assert len(dm.objections["universal"]) == 8

    def test_product_names(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        names = [p["name"] for p in dm.pricing["products"]]
        assert "AI SEO + GEO Audit" in names
        assert "AI SEO Services" in names
        assert "Website Build" in names
        assert "RAG Chatbot" in names
        assert "AI Workflows" in names

    def test_pricing_floors(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        for product in dm.pricing["products"]:
            if product["name"] == "AI SEO + GEO Audit":
                assert product["price"] == 149
                assert product["floor"] == 119
            elif product["name"] == "AI SEO Services":
                assert product["price"] == 500
                assert product["floor"] == 400

    def test_on_change_callback(self):
        called = []
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shutil.copy(DATA_DIR / "pricing.yaml", tmp / "pricing.yaml")
            shutil.copy(DATA_DIR / "objections.yaml", tmp / "objections.yaml")
            dm = DataManager(tmp)
            dm.load()
            dm.on_change(lambda: called.append(True))
            dm.save_pricing(dm.pricing)
            assert len(called) == 1


class TestPrompts:
    def test_pricing_prompt_contains_products(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        prompt = build_pricing_prompt(dm.pricing, dm.objections)
        assert "AI SEO + GEO Audit" in prompt
        assert "149" in prompt
        assert "floor" in prompt.lower()

    def test_pricing_prompt_contains_objections(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        prompt = build_pricing_prompt(dm.pricing, dm.objections)
        assert "Let me think about it" in prompt
        assert "burned by agencies" in prompt.lower()

    def test_pricing_prompt_with_proposal_bot(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        prompt = build_pricing_prompt(dm.pricing, dm.objections, proposal_bot_id=999)
        assert "<@999>" in prompt
        assert "proposal" in prompt.lower()

    def test_pricing_prompt_without_proposal_bot(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        prompt = build_pricing_prompt(dm.pricing, dm.objections, proposal_bot_id=None)
        assert "Proposal Handoff" not in prompt

    def test_manager_prompt_contains_pricing(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        prompt = build_manager_prompt(dm.pricing, dm.objections, ["pricing_agent"])
        assert "AI SEO + GEO Audit" in prompt
        assert "pricing_agent" in prompt

    def test_prompts_not_empty(self):
        dm = DataManager(DATA_DIR)
        dm.load()
        p = build_pricing_prompt(dm.pricing, dm.objections)
        m = build_manager_prompt(dm.pricing, dm.objections, ["pricing_agent"])
        assert len(p) > 1000
        assert len(m) > 1000


class TestMemory:
    def test_add_and_get(self):
        mem = ChannelMemory(max_messages=5)
        mem.add(1, "user", "hello")
        mem.add(1, "assistant", "hi")
        msgs = mem.get_messages(1)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["content"] == "hi"

    def test_max_messages(self):
        mem = ChannelMemory(max_messages=3)
        for i in range(5):
            mem.add(1, "user", f"msg {i}")
        msgs = mem.get_messages(1)
        assert len(msgs) == 3
        assert msgs[0]["content"] == "msg 2"

    def test_clear(self):
        mem = ChannelMemory()
        mem.add(1, "user", "hello")
        mem.clear(1)
        assert len(mem.get_messages(1)) == 0

    def test_separate_channels(self):
        mem = ChannelMemory()
        mem.add(1, "user", "channel 1")
        mem.add(2, "user", "channel 2")
        assert len(mem.get_messages(1)) == 1
        assert len(mem.get_messages(2)) == 1


class TestSetNested:
    def test_simple_path(self):
        data = {"a": {"b": 1}}
        _set_nested(data, "a.b", 2)
        assert data["a"]["b"] == 2

    def test_list_index(self):
        data = {"items": [{"price": 100}, {"price": 200}]}
        _set_nested(data, "items[1].price", 250)
        assert data["items"][1]["price"] == 250

    def test_deep_path(self):
        data = {"a": {"b": {"c": {"d": "old"}}}}
        _set_nested(data, "a.b.c.d", "new")
        assert data["a"]["b"]["c"]["d"] == "new"
