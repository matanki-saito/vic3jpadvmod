import unittest
import main


class TestStringMethods(unittest.TestCase):
    def test_issue242_1(self):
        result = main.issue_242("[Concept('neko neko',   '$concept_observer$')]としてプレイ")
        self.assertEqual(result, "[Concept('neko neko','$concept_observer$')]としてプレイ")

    def test_issue242_2(self):
        result = main.issue_242("の原因が考えられます：\n#indent_newline:2• セーブデー")
        self.assertEqual(result, "の原因が考えられます：\n#indent_newline:2 •セーブデー")

    def test_issue242_3(self):
        result = main.issue_242("#tooltippable_name #tooltip:$TAG$|$COMMANDER_RANK_TAG$,DATA_CHARACTER_RANK_NAME_FORMAT_TOOLTIP,CommanderRankTooltip  $NAME$#!#!")
        self.assertEqual(result, "#tooltippable_name #tooltip:$TAG$|$COMMANDER_RANK_TAG$,DATA_CHARACTER_RANK_NAME_FORMAT_TOOLTIP,CommanderRankTooltip $NAME$#!#!")

    def test_issue241_1(self):
        result = main.issue_241("#variable [COUNTRY.GetAdjectiveNoFormatting]#!の~[concept_relations] (対-#variable [TARGET_COUNTRY.GetName]#!) が$VALUE|0-$悪化しました")
        self.assertEqual(result, "#variable [COUNTRY.GetAdjectiveNoFormatting]#!の ～ [concept_relations] (対 ～ #variable [TARGET_COUNTRY.GetName]#!) が$VALUE|0-$悪化しました")

    def test_issue241_2(self):
        result = main.issue_241("[GOODS.GetName]で[Concept('concept_consumption_tax', '$concept_consumption_taxes$')]を回収中: #variable #N -$VAL|0$#!#!")
        self.assertEqual(result, "[GOODS.GetName]で[Concept('concept_consumption_tax', '$concept_consumption_taxes$')]を回収中 : #variable #N -$VAL|0$#!#!")

    def test_issue241_3(self):
        result = main.issue_241("$[DATE_MIN.GetStringShort|V]$ - $[DATE_MAX.GetStringShort|V]$")
        self.assertEqual(result, "$[DATE_MIN.GetStringShort|V]$ ～ $[DATE_MAX.GetStringShort|V]$")

    def test_issue241_4(self):
        result = main.issue_241("約#variable @money!$MIN_PER_LEVEL_WAGE$#!-#variable @money!$MAX_PER_LEVEL_WAGE$#!/レベル (公務員の給金) ")
        self.assertEqual(result, "約#variable @money!$MIN_PER_LEVEL_WAGE$#! ～ #variable @money!$MAX_PER_LEVEL_WAGE$#!/レベル (公務員の給金) ")

    def test_issue241_5(self):
        result = main.issue_241("$MIN$-$MAX$週")
        self.assertEqual(result, "$MIN$ ～ $MAX$週")

    def test_issue241_6(self):
        result = main.issue_241("$DAYS_MIN$-$DAYS_MAX$週")
        self.assertEqual(result, "$DAYS_MIN$ ～ $DAYS_MAX$週")

    def test_issue241_7(self):
        result = main.issue_241("$DURATION_MIN$-$DURATION_MAX$週")
        self.assertEqual(result, "$DURATION_MIN$ ～ $DURATION_MAX$週")

    def test_issue241_8(self):
        result = main.issue_241("#tooltippable_name #tooltip:$TAG$|$COMMANDER_RANK_TAG$,DATA_CHARACTER_RANK_NAME_FORMAT_TOOLTIP,CommanderRankTooltip  $NAME$#!#!")
        self.assertEqual(result, "#tooltippable_name #toolt ip:$TAG$|$COMMANDER_RANK_TAG$,DATA_CHARACTER_RANK_NAME_FORMAT_TOOLTIP,CommanderRankTooltip $NAME$#!#!")

    def test_issue241_9(self):
        result = main.issue_241("#test_tag;nullpo;TOOLTIP:$tag|+=-0$ [testFunction('hoge-hoge xx', scope.geso)|0],は0-5で(テスト)で（あ）る.#!;Aである:は正。-攻撃側有利")
        self.assertEqual(result, "#test_tag;nullpo;TOOLTIP:$tag|+=-0$ [testFunction('hoge-hoge xx', scope.geso)|0]、は0 ～ 5で (テスト) で (あ) る。#!つまりAである : は正。－攻撃側有利")

    def test_issue241_10(self):
        result = main.issue_241("[DIPLOMATIC_PLAY.GetName]の深刻度が$VALUE|-$増加しました")
        self.assertEqual(result, "[DIPLOMATIC_PLAY.GetName]の深刻度が$VALUE|-$増加しました")

    def test_issue241_11(self):
        result = main.issue_241("植民地の維持 : #N #BOLD -$MAINTENANCE|1$#!#!\n")
        self.assertEqual(result, "植民地の維持 : #N #BOLD -$MAINTENANCE|1$#!#!\n")

    def test_issue241_12(self):
        result = main.issue_241("#tooltippable_name #tooltip:$TAG$,DATA_FRONT_NAME_TOOLTIP,FrontTooltip $NAME$#!#!")
        self.assertEqual(result, "#tooltippable_name #tooltip:$TAG$,DATA_FRONT_NAME_TOOLTIP,FrontTooltip $NAME$#!#!")

    def test_issue241_13(self):
        result = main.issue_241("[concept_state]: [Pop.GetState.GetName]\n[concept_culture]: [Pop.GetCulture.GetName]\n[concept_religion]: [Pop.GetReligion.GetName]\nWorks at: [Pop.GetWorksAt]\n[ConcatIfNeitherEmpty(Pop.GetSharesDesc, '\n')]\n[Concept('concept_pop','$concept_population$')]: #tooltippable #tooltip:[Pop.GetTooltipTag],POP_POPULATION [Pop.GetTotalSize|Dv]#!#! (#tooltippable #tooltip:[Pop.GetTooltipTag],POP_POPULATION_GROWTH #variable [Pop.GetPopGrowth|+=D]#!#!#!)\n[concept_workforce]: #tooltippable #tooltip:[Pop.GetTooltipTag],POP_WORKFORCE_TOOLTIP [Pop.GetNumWorkforce|Dv]#!#!\n[concept_dependents]: #tooltippable #tooltip:[Pop.GetTooltipTag],POP_DEPENDENTS_TOOLTIP [Pop.GetDependentsSize|Dv]#!#!\n\nStrata: [Pop.GetPopType.GetStrata]\n[concept_sol]: #tooltippable #tooltip:[Pop.GetTooltipTag],TOOLTIP_POP_QOL [Pop.GetFormattedStandardOfLivingLabel|v] ([Pop.GetFormattedStandardOfLiving|v])#!#!\nNet Income: #variable @money![Pop.GetMoney|D=+]#!\n[concept_wealth]: #tooltippable #tooltip:[Pop.GetTooltipTag],TOOLTIP_WEALTH [Pop.GetCurrentWealth|v]#!#!\n\n$POP_DISCRIMINATION_HEADER$ #tooltippable #tooltip:[Pop.GetTooltipTag],POP_DISCRIMINATION_STATUS_TOOLTIP [SelectLocalization(Pop.IsDiscriminated, 'POP_DISCRIMINATION_STATUS_DISCRIMINATED', 'POP_DISCRIMINATION_STATUS_ACCEPTED')]#!#!\n[concept_literacy]: #tooltippable #tooltip:[Pop.GetTooltipTag],POP_POPULATION_LITERACY [Pop.GetLiteracyRate|%1v]#!#!\n\nPrimary [concept_interest_group]: [Pop.GetLargestInterestGroup.GetName]\n[concept_political_strength]: #tooltippable #tooltip:[Pop.GetTooltipTag],POP_POL_STR [Pop.GetPoliticalStrength|Kv]#!#!\n$RADICALS$: #variable [Pop.GetNumRadicals|D]#!\n$LOYALISTS$: #variable [Pop.GetNumLoyalists|D]#![ConcatIfNeitherEmpty('\n\n',Pop.GetPoliticalMovementsDesc)]")
        self.assertEqual(result, "[concept_state]xxxx : [Pop.GetState.GetName]\n[concept_culture]xxxx : [Pop.GetCulture.GetName]\n[concept_religion]xxxx : [Pop.GetReligion.GetName]\n就労場所xxxx : [Pop.GetWorksAt]\n[ConcatIfNeitherEmpty(Pop.GetSharesDesc, '\n')]\n[Concept('concept_pop','$concept_population$')]xxxx : #tooltippable #tooltipxxxx : [Pop.GetTooltipTag],POP_POPULATION [Pop.GetTotalSize|Dv]#!#! (#tooltippable #tooltipxxxx : [Pop.GetTooltipTag],POP_POPULATION_GROWTH #variable [Pop.GetPopGrowth|+=D]#!#!#!)\n[concept_workforce]xxxx : #tooltippable #tooltipxxxx : [Pop.GetTooltipTag],POP_WORKFORCE_TOOLTIP [Pop.GetNumWorkforce|Dv]#!#!\n[concept_dependents]xxxx : #tooltippable #tooltipxxxx : [Pop.GetTooltipTag],POP_DEPENDENTS_TOOLTIP [Pop.GetDependentsSize|Dv]#!#!\n\n階級xxxx : [Pop.GetPopType.GetStrata]\n[concept_sol]xxxx : #tooltippable #tooltipxxxx : [Pop.GetTooltipTag],TOOLTIP_POP_QOL [Pop.GetFormattedStandardOfLivingLabel|v] ([Pop.GetFormattedStandardOfLiving|v])#!#!\n純利益xxxx : #variable @money![Pop.GetMoney|D=+]#!\n[concept_wealth]xxxx : #tooltippable #tooltipxxxx : [Pop.GetTooltipTag],TOOLTIP_WEALTH [Pop.GetCurrentWealth|v]#!#!\n\n$POP_DISCRIMINATION_HEADER$ #tooltippable #tooltipxxxx : [Pop.GetTooltipTag],POP_DISCRIMINATION_STATUS_TOOLTIP [SelectLocalization(Pop.IsDiscriminated, 'POP_DISCRIMINATION_STATUS_DISCRIMINATED', 'POP_DISCRIMINATION_STATUS_ACCEPTED')]#!#!\n[concept_literacy]xxxx : #tooltippable #tooltipxxxx : [Pop.GetTooltipTag],POP_POPULATION_LITERACY [Pop.GetLiteracyRate|%1v]#!#!\n\n主要[concept_interest_group]xxxx : [Pop.GetLargestInterestGroup.GetName]\n[concept_political_strength]xxxx : #tooltippable #tooltipxxxx : [Pop.GetTooltipTag],POP_POL_STR [Pop.GetPoliticalStrength|Kv]#!#!\n$RADICALS$xxxx : #variable [Pop.GetNumRadicals|D]#!\n$LOYALISTS$xxxx : #variable [Pop.GetNumLoyalists|D]#![ConcatIfNeitherEmpty('\n\n',Pop.GetPoliticalMovementsDesc)]")

    def test_issue241_14(self):
        result = main.issue_241("[concept_clout]: #tooltippable #tooltip:[InterestGroup.GetTooltipTag],IG_CLOUT_BREAKDOWN,IGCloutTooltip [InterestGroup.GetClout|%1]#!#![InterestGroup.GetInfluenceDesc]\n[AddLocalizationIf(InterestGroup.HasParty, 'PARTY_DESC')][Concept('concept_ideology', '$concept_ideologies$')]: [InterestGroup.GetIdeologyDesc]\n[concept_leader]: [InterestGroup.GetLeader.GetFullName] ([InterestGroup.GetLeaderIdeologyDesc])\n\n[concept_approval]: #tooltippable #tooltip:IG_APPROVAL_BREAKDOWN [InterestGroup.GetApprovalRating] #bold ([InterestGroup.GetApprovalValue|+=])#!#!#!\n[Concept('concept_interest_group_trait', '$concept_interest_group_traits$')]:\n[InterestGroup.GetTraitsDesc]\n\n人口: [InterestGroup.GetPopulation|Kv]\n[InterestGroup.GetSupportingPopTypesDesc][ConcatIfNeitherEmpty('\n\n',InterestGroup.GetPoliticalMovementDesc)]")
        self.assertEqual(result,"")

if __name__ == '__main__':
    unittest.main()
