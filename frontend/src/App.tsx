import {useCallback,useEffect,useState} from 'react';
import {BarChart3,BriefcaseBusiness,Bot,ChevronLeft,ChevronRight,LayoutDashboard,PlusCircle,UserRound} from 'lucide-react';
import {api} from './api';
import type {Job,Page} from './types';
import {Overview} from './pages/Overview';
import {Pipeline} from './pages/Pipeline';
import {Jobs} from './pages/Jobs';
import {AddJobs} from './pages/AddJobs';
import {Assistant} from './pages/Assistant';
import {ProfilePage} from './pages/Profile';

const nav:Array<{page:Page;icon:typeof LayoutDashboard}>=[
  {page:'Overview',icon:LayoutDashboard},{page:'Pipeline',icon:BarChart3},{page:'Jobs',icon:BriefcaseBusiness},
  {page:'Add jobs',icon:PlusCircle},{page:'AI assistant',icon:Bot},{page:'Profile',icon:UserRound}
];

export default function App(){
  const [page,setPage]=useState<Page>('Overview');const [jobs,setJobs]=useState<Job[]>([]);const [loading,setLoading]=useState(true);const [collapsed,setCollapsed]=useState(false);const [error,setError]=useState('');
  const refresh=useCallback(async()=>{try{setJobs(await api.jobs());setError('')}catch(e){setError(e instanceof Error?e.message:'Cannot load jobs')}finally{setLoading(false)}},[]);
  useEffect(()=>{refresh();const timer=setInterval(refresh,4000);return()=>clearInterval(timer)},[refresh]);
  const completed=jobs.filter(j=>j.processing_status==='completed');
  return <div className={`app-shell ${collapsed?'sidebar-collapsed':''}`}>
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">N</div>{!collapsed&&<div><strong>NEXUS</strong><span>Career intelligence</span></div>}</div>
      <nav>{nav.map(({page:item,icon:Icon})=><button key={item} className={page===item?'active':''} onClick={()=>setPage(item)} title={item}><Icon size={18}/>{!collapsed&&<span>{item}</span>}{item==='Add jobs'&&!collapsed&&jobs.some(j=>j.processing_status==='queued')&&<i>{jobs.filter(j=>j.processing_status==='queued').length}</i>}</button>)}</nav>
      <div className="sidebar-footer">{!collapsed&&<><div className="model-dot"><span/>Ollama local</div><small>{completed.length} indexed jobs</small></>}<button className="collapse" onClick={()=>setCollapsed(!collapsed)}>{collapsed?<ChevronRight size={17}/>:<ChevronLeft size={17}/>}</button></div>
    </aside>
    <main className="workspace">
      {error&&<div className="error-banner">{error}</div>}
      {loading?<div className="loader">Loading your pipeline…</div>:<>
        {page==='Overview'&&<Overview jobs={jobs} navigate={setPage}/>} 
        {page==='Pipeline'&&<Pipeline jobs={completed} refresh={refresh}/>} 
        {page==='Jobs'&&<Jobs jobs={jobs} refresh={refresh}/>} 
        {page==='Add jobs'&&<AddJobs jobs={jobs} refresh={refresh}/>} 
        {page==='AI assistant'&&<Assistant/>} 
        {page==='Profile'&&<ProfilePage/>}
      </>}
    </main>
  </div>
}
