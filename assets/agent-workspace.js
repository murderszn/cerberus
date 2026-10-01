/* Compose one workspace from the existing, functional scanner controls. */
(function () {
    'use strict';
    document.body.classList.add('workspace-page');
    function node(tag, cls, text) { var n=document.createElement(tag); if(cls)n.className=cls; if(text)n.textContent=text; return n; }
    function wrapDetails(element, title) {
        if (!element) return;
        var details=node('details','workspace-disclosure');
        details.append(node('summary','',title)); element.before(details); details.append(element);
    }
    var splash=document.getElementById('view-splash');
    var shell=node('div','mission-control-grid');
    var briefing=node('div','mission-briefing');
    while(splash.firstChild) briefing.append(splash.firstChild);
    var hero=node('div','mission-header');
    hero.append(node('p','workspace-kicker','CERBERUS / REPOSITORY SECURITY'),
        node('h1','','See the risk.\nFind the evidence.'),
        node('p','','Nine specialists examine the repository. Use your Pollinations balance for Jev review decisions and a clear AI brief.'));
    briefing.prepend(hero);
    shell.append(briefing);
    splash.append(shell);
    var consent=document.querySelector('.jev-consent');
    var form=document.getElementById('target-form');
    if (consent && form) form.after(consent);
    var run=document.getElementById('run-btn'); if(run) run.textContent='Scan repository ↗';
    var note=document.querySelector('.entry-note'); if(note) note.textContent='Public repositories scan immediately. Connect GitHub for account and repository access.';
    var examples=document.querySelector('.example-repositories') || document.querySelector('#view-splash .chips');
    if(examples) {
        examples.querySelectorAll('.chip').forEach(function(chip,i) { if(i>1) chip.hidden=true; });
        var sample=examples.querySelector('.sample-report-link'); if(sample) sample.textContent='Sample report →';
    }
    wrapDetails(document.querySelector('.github-agent-onboarding'),'Use Cerberus in GitHub');

    function stage(id, isReport) {
        var view=document.getElementById(id);
        var stage=node('div','workspace-stage');
        var intelligence=node('section','workspace-intelligence');
        intelligence.id=isReport?'workspace-report-jev':'workspace-scan-jev';
        var empty=node('div','workspace-jev-empty');
        empty.append(node('p','workspace-kicker','JEV / FILE INTELLIGENCE'),node('h2','','The order before\nthe investigation.'),node('p','','Build the Jev review queue above to group findings by next action. Local source triage is also available with the TypeSafe bridge.'));
        intelligence.append(empty);
        var specialists=node('section','workspace-specialists');
        specialists.append(node('p','workspace-kicker','CERBERUS / SPECIALIST POOL'),node('h2','',isReport?'The evidence, by domain.':'Nine perspectives. In motion.'));
        var grid=document.getElementById(isReport?'report-agent-grid':'scan-agent-grid');
        if(grid) specialists.append(grid);
        specialists.append(node('p','workspace-pool-note',isReport?'Select a specialist to filter its findings. Curator synthesis does not change the native score.':'Statuses reflect actual check execution. Jev assesses the same revision after native checks finish.'));
        stage.append(intelligence,specialists);
        if(!isReport) {
            var loader=document.getElementById('pack-loader');
            view.insertBefore(stage,loader);
            specialists.append(loader);
        }
        return stage;
    }
    stage('view-scan',false);
    var reportStage=stage('view-report',true);
    var reportView=document.getElementById('view-report');
    var scorecard=document.getElementById('jules-view-scorecard');
    var header=scorecard ? scorecard.querySelector('.report-header') : null;
    var actions=scorecard ? scorecard.querySelector('.report-actions') : null;
    var tabs=document.querySelector('.jules-tab-strip');

    if(header && reportView) {
        header.classList.add('workspace-report-header');
        reportView.prepend(header);
        var score=scorecard.querySelector('.score-container-box');
        if(score) header.append(score);
        var overviewHeading=header.querySelector('h1');
        if(overviewHeading) overviewHeading.textContent='Repository intelligence';
    }
    if(actions && header) {
        actions.classList.add('workspace-report-actions');
        header.after(actions);
    }
    if(tabs && actions) {
        actions.after(tabs);
    }
    if(scorecard && reportStage) {
        scorecard.prepend(reportStage);
    }

    var labels = {
        'tab-failed-btn': 'Failed checks',
        'tab-scorecard-btn': 'Findings',
        'tab-pr-btn': 'Review patches',
        'tab-plan-btn': 'Engineering plan',
        'tab-console-btn': 'Ask Cerberus'
    };
    Object.keys(labels).forEach(function(id) {
        var tab=document.getElementById(id);
        if(!tab) return;
        var labelEl=tab.querySelector('.tab-label');
        if(labelEl) labelEl.textContent=labels[id];
    });

    var grid=document.getElementById('report-agent-grid');
    if(grid) grid.addEventListener('click',function(e) {
        if(e.target.closest('[role="checkbox"],button,.agent-card-mini')) {
            var scBtn = document.getElementById('tab-scorecard-btn');
            if(scBtn) scBtn.click();
        }
    });
    wrapDetails(document.querySelector('.scan-log-wrap'),'Execution log');
    window.addEventListener('cerberus:report',function(e) {
        var jevPanel = document.getElementById('workspace-report-jev');
        if (jevPanel) jevPanel.classList.toggle('has-jev',!!e.detail.triage);
    });
})();
