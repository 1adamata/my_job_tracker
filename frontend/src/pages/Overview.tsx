import type {ReactNode} from 'react';
import {ArrowRight,CalendarClock,CheckCircle2,Send,Target,Trophy,type LucideIcon} from 'lucide-react';
import type {Job,Page} from '../types';
import {PageHeader} from '../components/PageHeader';

export function Overview({jobs,navigate}:{jobs:Job[];navigate:(p:Page)=>void}){
  const done=jobs.filter(j=>j.result);
  const count=(stage:string)=>done.filter(j=>j.result?.status===stage).length;
  const interviews=['Phone Screen','Assessment','Final Interview'].reduce((n,s)=>n+count(s),0);
  const deadlines=done.filter(j=>j.result?.deadline&&new Date(j.result.deadline)>new Date()).length;
  const stats:Array<{label:string;value:number;Icon:LucideIcon;color:string}>=[
    {label:'Saved opportunities',value:done.length,Icon:Target,color:'blue'},
    {label:'Applications sent',value:count('Applied'),Icon:Send,color:'violet'},
    {label:'Interview stages',value:interviews,Icon:CheckCircle2,color:'green'},
    {label:'Offers',value:count('Offer'),Icon:Trophy,color:'amber'}
  ];
  const stages=['To Apply','Applied','Phone Screen','Assessment','Final Interview','Offer','Rejected'];
  const max=Math.max(...stages.map(count),1);
  return <>
    <PageHeader eyebrow="DASHBOARD" title="Good afternoon, Nurassyl" description="A clear view of your graduate application season." actions={<button className="primary-btn" onClick={()=>navigate('Add jobs')}>Add opportunities <ArrowRight size={16}/></button>}/>
    <section className="metric-grid">{stats.map(({label,value,Icon,color})=><article className="metric-card" key={label}><div className={`metric-icon ${color}`}><Icon size={19}/></div><span>{label}</span><strong>{value}</strong><small>{label==='Saved opportunities'?'Across your local tracker':'Updated from application stages'}</small></article>)}</section>
    <div className="overview-grid">
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">PIPELINE HEALTH</span><h2>Applications by stage</h2></div><button className="text-btn" onClick={()=>navigate('Pipeline')}>Open board <ArrowRight size={14}/></button></div><div className="stage-chart">{stages.map(stage=><div className="bar-row" key={stage}><span>{stage}</span><div><i style={{width:`${Math.max((count(stage)/max)*100,count(stage)?4:0)}%`}}/></div><strong>{count(stage)}</strong></div>)}</div></section>
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">ACTION CENTER</span><h2>What needs attention</h2></div></div><Action icon={<CalendarClock/>} value={deadlines} title="Upcoming deadlines" text="Vacancies with a future recorded deadline"/><Action icon={<Send/>} value={count('To Apply')} title="Ready to apply" text="Saved roles still waiting for submission"/><Action icon={<CheckCircle2/>} value={jobs.filter(j=>j.processing_status==='failed').length} title="Extraction issues" text="Captured pages that may need a retry"/></section>
    </div>
    <section className="panel recent"><div className="panel-head"><div><span className="eyebrow">RECENTLY CAPTURED</span><h2>Latest opportunities</h2></div><button className="text-btn" onClick={()=>navigate('Jobs')}>View all <ArrowRight size={14}/></button></div><div className="recent-table">{done.slice(0,6).map(j=><div key={j.id}><div className="company-avatar">{(j.result?.company_name||'?').slice(0,1)}</div><span><strong>{j.result?.role_title}</strong><small>{j.result?.company_name} · {j.result?.location}</small></span><em>{j.result?.status}</em></div>)}</div></section>
  </>
}

function Action({icon,value,title,text}:{icon:ReactNode;value:number;title:string;text:string}){return <div className="action-row"><div className="action-icon">{icon}</div><span><strong>{title}</strong><small>{text}</small></span><b>{value}</b></div>}
