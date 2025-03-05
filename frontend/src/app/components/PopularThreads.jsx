import React from 'react';

function PopularThreads(){
    return(
<div className='container text-yellow-400 mx-auto px-4 py-2'>
         <div>
            <h1 className='text-xl  px-4 font-bold bg-blue-500'>Hilos Populares</h1>
        </div>
        <div className='flex flex-col border justify-center px-4 py-4 space-y-4 md:flex-row md:space-y-0'>
        <div className='pr-4 flex flex-col items-center'>
                    <h2>Historia</h2>
                    <img
                        src='https://dominicantoday.com/wp-content/uploads/2023/07/presidente-medina-triste-741x486-1.jpg'
                        className='h-15 w-12' 
                    />
                    <h3>/h/ </h3>
                    <p>PERO VEAN A ETE MAMABINBIN</p>
                    <p className='font-bold'>u/anonymous</p>
                </div>

                <div className='pr-4 flex flex-col items-center'>
                    <h2>Anime</h2>
                    <img
                        src='https://beebom.com/wp-content/uploads/2023/04/Hiruko-form.jpg?w=431'
                        className='h-15 w-12' 
                    />
                    <h3>/a/ </h3>
                    <p>to eso tigere que tu ve con esa carita
                        de mmg son malisimo</p>
                    <p className='font-bold'>u/anonymous</p>
                </div>

                <div className='pr-4 flex flex-col items-center'>
                    <h2>Armas</h2>
                    <img
                        src='https://modernfirearms.net/userfiles/images/smg/belgium/1287829349.jpg'
                        className='h-15 w-13' 
                    />
                    <h3>/wa/</h3>
                    <p>si tan solo fueran legales :( </p>
                    <p className='font-bold'>u/anonymous</p>
                </div>

                <div className='pr-4 flex flex-col items-center'>
                    <h2>Cultura</h2>
                    <img
                        src='https://www.barcelo.com/guia-turismo/wp-content/uploads/2020/11/carnaval-dominicano_300.jpg'
                        className='h-15 w-13' 
                    />
                    <h3>/cu/</h3>
                    <p>quien ha ido al carnaval?</p>
                    <p className='font-bold'>u/anonymous</p>
                </div>

                <div className='pr-4 flex flex-col items-center'>
                    <h2>Random</h2>
                    <img
                        src='https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Luis_Abinader_en_2022.jpg/220px-Luis_Abinader_en_2022.jpg'
                        className='h-13 w-12' 
                    />
                    <h3>/r/ </h3>
                    <p>quien gana eta vuelta? </p>
                    <p className='font-bold'>u/anonymous</p>
                </div>

                <div className='pr-4 flex flex-col items-center'>
                    <h2>18+</h2>
                    <img
                        src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ68cdXUTq8P1llGDt8Uz7najjnQCqFABSV7jG4wt9Qm5u6cN462MxMsvPtQBCfvL9Aoy0&usqp=CAU'
                        className='h-15 w-12' 
                    />
                    <h3>/XX/</h3>
                    <p>bueno yo si le diera a Haku</p>
                    <p className='font-bold'>u/anonymous</p>
                </div>

        </div>
    </div>
    )
}
export default PopularThreads