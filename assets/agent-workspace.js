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
        node('p','','Nine specialists examine the repository. Jev orders the files for review. Pollinations can turn the findings into a clear brief.'));
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
        empty.append(node('p','workspace-kicker','JEV / FILE INTELLIGENCE'),node('h2','','The order before\nthe investigation.'),node('p','','Enable Jev before a scan to watch files become a prioritized review queue. Native security checks work independently.'));
        intelligence.append(empty);
        var specialists=node('section','workspace-specialists');
        specialists.append(node('p','workspace-kicker','CERBERUS / SPECIALIST POOL'),node('h2','',isReport?'The evidence, by domain.':'Nine perspectives. In motion.'));
        var grid=document.getElementById(isReport?'report-agent-grid':'scan-agent-grid');
        if(grid) specialists.append(grid);
        specialists.append(node('p','workspace-pool-note',isReport?'Select a specialist to filter its findings. Curator synthesis does not change the native score.':'Statuses reflect actual check execution. Jev assesses the same revision after native checks finish.'));
        stage.append(intelligence,specialists);
        if(isReport) view.prepend(stage);
        else {
            var loader=document.getElementById('pack-loader');
            view.insertBefore(stage,loader);
            specialists.append(loader);
        }
        return stage;
    }
    stage('view-scan',false);
    var reportStage=stage('view-report',true);
    var scorecard=document.getElementById('jules-view-scorecard');
    if(scorecard) {
        var header=scorecard.querySelector('.report-header');
        if(header) { header.classList.add('workspace-report-header'); reportStage.before(header); }
        var score=scorecard.querySelector('.score-container-box');
        if(score && header) header.append(score);
        var overviewHeading=header && header.querySelector('h1'); if(overviewHeading) overviewHeading.textContent='Repository intelligence';
        var actions=scorecard.querySelector('.report-actions');
        if(actions) { actions.classList.add('workspace-report-actions'); reportStage.before(actions); }
    }
    var labels={'tab-scorecard-btn':'Findings','tab-console-btn':'Ask Cerberus','tab-pr-btn':'Review patches','tab-plan-btn':'Engineering plan'};
    Object.keys(labels).forEach(function(id) { var tab=document.getElementById(id); if(tab) tab.textContent=labels[id]; });
    var tabs=document.querySelector('.jules-tab-strip');
    if(tabs) tabs.prepend(document.getElementById('tab-scorecard-btn'));
    var grid=document.getElementById('report-agent-grid');
    if(grid) grid.addEventListener('click',function(e) { if(e.target.closest('[role="checkbox"],button,.agent-card-mini')) document.getElementById('tab-scorecard-btn').click(); });
    wrapDetails(document.querySelector('.scan-log-wrap'),'Execution log');
    window.addEventListener('cerberus:report',function(e) {
        document.getElementById('workspace-report-jev').classList.toggle('has-jev',!!e.detail.triage);
    });
})();
