"""Shift autoloot observes key transitions rather than render frames."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]

def runtime():
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
        left=false;right=false;writes={}
        function IsLeftShiftKeyDown() return left end
        function IsRightShiftKeyDown() return right end
        function IsShiftKeyDown() return left or right end
        function SetAutoloot(value) writes[#writes+1]=value end
        SuperAPI={db={profile={}},frame={events={},scripts={}}}
        function SuperAPI:RegisterDefaults() end
        function SuperAPI.frame:RegisterEvent(e) self.events[e]=true end
        function SuperAPI.frame:UnregisterEvent(e) self.events[e]=nil end
        function SuperAPI.frame:SetScript(e,fn) self.scripts[e]=fn end
        function modifier(key,down)
            if key=='LSHIFT' then left=down elseif key=='RSHIFT' then right=down end
            if SuperAPI.frame.events.MODIFIER_STATE_CHANGED then
                event='MODIFIER_STATE_CHANGED';arg1=key;arg2=down and 1 or 0
                SuperAPI:OnEvent()
            end
        end
    """)
    s=(ROOT/'SuperAPIOptions.lua').read_text(encoding='utf-8-sig')
    lua.execute(s[:s.index('SuperAPI.cmdtable =')])
    s=(ROOT/'SuperAPI.lua').read_text(encoding='utf-8-sig')
    lua.execute(s[s.index('function SuperAPI:OnEvent()'):s.index('-- HOOKS --')])
    return lua

class AutolootEventsTests(unittest.TestCase):
    def test_shift_mode_has_no_render_callback_and_handles_both_shift_keys(self):
        lua=runtime()
        lua.execute("""
            SuperAPI.ConfigureAutoloot(SuperAPI.AUTOLOOT_OPTIONS[3])
            assert(SuperAPI.frame.events.MODIFIER_STATE_CHANGED and not SuperAPI.frame.scripts.OnUpdate)
            assert(#writes==1 and writes[1]==0)
            modifier('LSHIFT',true);assert(writes[#writes]==1)
            modifier('RSHIFT',true);modifier('LSHIFT',false)
            assert(writes[#writes]==1,'Either held Shift key enables autoloot')
            modifier('RSHIFT',false);assert(writes[#writes]==0)
            local n=#writes;modifier('LCTRL',true);assert(#writes==n)
        """)

    def test_inverse_mode_and_static_modes_apply_live_and_release_observer(self):
        lua=runtime()
        lua.execute("""
            modifier('RSHIFT',true)
            SuperAPI.ConfigureAutoloot(SuperAPI.AUTOLOOT_OPTIONS[4]);assert(writes[#writes]==0)
            modifier('RSHIFT',false);assert(writes[#writes]==1)
            SuperAPI.ConfigureAutoloot(SuperAPI.AUTOLOOT_OPTIONS[1])
            assert(writes[#writes]==1 and not SuperAPI.frame.events.MODIFIER_STATE_CHANGED)
            local n=#writes;modifier('LSHIFT',true);assert(#writes==n)
            SuperAPI.ConfigureAutoloot(SuperAPI.AUTOLOOT_OPTIONS[2]);assert(writes[#writes]==0)
            assert(not SuperAPI.frame.events.MODIFIER_STATE_CHANGED and not SuperAPI.frame.scripts.OnUpdate)
        """)

    def test_focus_reconciled_left_right_state_does_not_use_stale_merged_query(self):
        lua=runtime()
        lua.execute("""
            IsShiftKeyDown=function() error('Merged native Shift state can be stale after focus loss') end
            SuperAPI.ConfigureAutoloot(SuperAPI.AUTOLOOT_OPTIONS[3])
            modifier('LSHIFT',true);assert(writes[#writes]==1)
            modifier('LSHIFT',false);assert(writes[#writes]==0)
        """)

    def test_capability_guard_reports_missing_event_or_key_queries_without_initializing(self):
        source=(ROOT/'SuperAPI.lua').read_text(encoding='utf-8-sig')
        prefix=source[:source.index('SuperAPI = AceLibrary')]
        for missing in ('event', 'left', 'right'):
            lua=runtime()
            lua.execute("""
                SUPERWOW_VERSION='2.2'; warnings=0
                DEFAULT_CHAT_FRAME={AddMessage=function() warnings=warnings+1 end}
                C_EventUtils={IsEventValid=function(event) return event=='MODIFIER_STATE_CHANGED' end}
            """)
            if missing=='event': lua.execute('C_EventUtils=nil')
            else: lua.execute('Is'+missing.capitalize()+'ShiftKeyDown=nil')
            lua.execute(prefix)
            lua.execute('assert(SuperAPI==nil and warnings==1)')

    def test_saved_setting_entry_uses_the_same_controller_as_live_changes(self):
        lua=runtime()
        s=(ROOT/'SuperAPIOptions.lua').read_text(encoding='utf-8-sig')
        begin=s.index('SuperAPI.cmdtable =')
        end=s.index('\t\tclickthrough = {',begin)
        lua.execute(s[begin:end]+'}}')
        lua.execute("""
            local entry=SuperAPI.cmdtable.args.autoloot
            entry.set(SuperAPI.AUTOLOOT_OPTIONS[3])
            assert(entry.get()==SuperAPI.AUTOLOOT_OPTIONS[3] and SuperAPI.frame.events.MODIFIER_STATE_CHANGED)
            entry.set(SuperAPI.AUTOLOOT_OPTIONS[2])
            assert(entry.get()==SuperAPI.AUTOLOOT_OPTIONS[2] and not SuperAPI.frame.events.MODIFIER_STATE_CHANGED)
        """)

if __name__=='__main__':unittest.main()
