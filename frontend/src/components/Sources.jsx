function Sources({

sources

}){

if(
!sources?.length
)
return null;

return(

<div
className="
mt-5
"
>

<p
className="
font-semibold
mb-2
"
>
Sources
</p>

<div
className="
flex
gap-3
flex-wrap
"
>

{
sources.map(
(source,i)=>(

<div
key={i}
className="
bg-slate-100
rounded-xl
px-4
py-2
"
>
📄 {source}
</div>

))
}

</div>

</div>

)

}

export default Sources;