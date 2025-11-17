#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import importlib
sys.path.insert(0, '.')
import down
importlib.reload(down)  # Force reload pour éviter le cache
from down import _fix_french_quotes


def test_fix_french_quotes():
    """Test de la fonction _fix_french_quotes avec différents cas"""
    
    test_cases = [
        # (input, expected_output, description)
        (
            '« non lus » étaient devenus « lus »',
            '« non lus » étaient devenus « lus »',
            'Cas correct - ne doit PAS être modifié'
        ),
        (
            '» non lus « étaient devenus » lus «',
            '« non lus » étaient devenus « lus »',
            'Cas mal ordonné - doit être corrigé'
        ),
        (
            '<p style="text-align:left;">Les messages précédemment « non lus » étaient devenus « lus ». Les mots lui disant qu\'il n\'avait pas lu les messages avaient disparu, mais il n\'avait plus l\'intention de continuer à entretenir ces illusions. Il sentait qu\'il en avait fait assez.</p>',
            '<p style="text-align:left;">Les messages précédemment « non lus » étaient devenus « lus ». Les mots lui disant qu\'il n\'avait pas lu les messages avaient disparu, mais il n\'avait plus l\'intention de continuer à entretenir ces illusions. Il sentait qu\'il en avait fait assez.</p>',
            'Cas HTML correct - ne doit PAS être modifié'
        ),
        (
            'Simple: » test «',
            'Simple: « test »',
            'Simple cas mal ordonné'
        ),
        (
            'Simple: « test »',
            'Simple: « test »',
            'Simple cas correct'
        ),
        (
            '» a « et » b «',
            '« a » et « b »',
            'Deux paires mal ordonnées'
        ),
        (
            '« a » et » b «',
            '« a » et « b »',
            'Une paire correcte et une mal ordonnée'
        ),
        (
            '» a « et « b »',
            '« a » et « b »',
            'Une paire mal ordonnée et une correcte'
        ),
        (
            '« a » et « b »',
            '« a » et « b »',
            'Deux paires correctes'
        ),
        (
            '» a « et » b « et » c «',
            '« a » et « b » et « c »',
            'Trois paires mal ordonnées'
        ),
        (
            'Pas de guillemets',
            'Pas de guillemets',
            'Pas de guillemets - ne doit pas changer'
        ),
        (
            'Seulement « ouvrant',
            'Seulement « ouvrant',
            'Seulement un guillemet ouvrant'
        ),
        (
            'Seulement » fermant',
            'Seulement » fermant',
            'Seulement un guillemet fermant'
        ),
        (
            '<p class="talk">« Si tu restes tendu comme ça, tu n\'auras même pas la chance de t\'enfuir avant d\'être mort, ok ? Ce que j\'essaie de dire, c\'est : « Détends-toi un peu. »</p>',
            '<p class="talk">« Si tu restes tendu comme ça, tu n\'auras même pas la chance de t\'enfuir avant d\'être mort, ok ? Ce que j\'essaie de dire, c\'est : « Détends-toi un peu. »</p>',
            'Guillemets imbriqués corrects - ne doit PAS être modifié'
        ),
        (
            'passée de » Main du Souverain » à » Autorité du Souverain «',
            'passée de « Main du Souverain » à « Autorité du Souverain »',
            'Trois guillemets consécutifs mal ordonnés'
        ),
        (
            'fondée sur la » Main du Souverain » commença',
            'fondée sur la « Main du Souverain » commença',
            'Paire mal ordonnée simple au milieu de texte'
        ),
    ]
    
    print('=' * 80)
    print('TEST DE LA FONCTION _fix_french_quotes')
    print('=' * 80)
    print()
    
    passed = 0
    failed = 0
    
    for i, (input_str, expected, description) in enumerate(test_cases, 1):
        result = _fix_french_quotes(input_str)
        success = result == expected
        
        if success:
            status = '✓ PASS'
            passed += 1
        else:
            status = '✗ FAIL'
            failed += 1
        
        print(f'{status} Test {i}: {description}')
        if not success:
            print(f'  Input:    {input_str}')
            print(f'  Expected: {expected}')
            print(f'  Got:      {result}')
            print()
    
    print('=' * 80)
    print(f'Résultats: {passed} réussis, {failed} échoués sur {len(test_cases)} tests')
    print('=' * 80)
    
    return failed == 0


if __name__ == '__main__':
    success = test_fix_french_quotes()
    sys.exit(0 if success else 1)

