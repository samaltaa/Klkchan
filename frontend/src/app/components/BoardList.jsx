import React from 'react';

function BoardList(){
    return(
        <div className='container text-yellow-400 mx-auto px-4 py-2'>
            <div>
                <h1 className='text-xl px-4 font-bold bg-blue-500'>Boards</h1>
            </div>
            <div className='flex felx-col text-yellow-400 border justify-center px-4 py-4 space-y-4 md:flex-row md-space-y-0'>
            <div className='pr-4'>
                    <h2 className='font-bold'>Hobbies</h2>
                    <ul>
                        <li>/a/ - Anime & Manga</li>
                        <li>/v/ - Video Juegos</li>
                        <li>/t/ - Torrents</li>
                        <li>/o/ - Autos</li>
                    </ul>
                </div>
                <div className='pr-4'>
                    <h2 className='font-bold'>Cultura</h2>
                    <ul>
                        <li>/tv/ - Television & Film</li>
                        <li>/mu/ - Musica</li>
                        <li>/lit/ - Literatura</li>
                        <li>/his/ - Historia & Humanidades</li>
                    </ul>
                </div>
                <div className='pr-4'>
                    <h2 className='font-bold'>Creatividad</h2>
                    <ul>
                        <li>/w/ - Wallpapers</li>
                        <li>/ic/ - Art/Dibujos/Criticismo</li>
                        <li>/po/ - Papercraft & Origami</li>
                        <li>/wg/ - Wallpapers/General</li>
                    </ul>
                </div>
                <div className='pr-4 '>
                    <h2 className='font-bold'>Technologia</h2>
                    <ul>
                        <li>/wa/ - Armas</li>
                        <li>/diy/ - Do It Yourself</li>
                        <li>/sci/ - Ciencia & Matematicas</li>
                        <li>/g/ - Tecnologia</li>
                    </ul>
                </div>
                <div className='pr-4'>
                    <h2 className='font-bold'>18+</h2>
                    <ul>
                        <li>/h/ - Hentai</li>
                        <li>/e/ - Ecchi</li>
                        <li>/d/ - Hentai/Alternative</li>
                        <li>/s/ - Sexy Beautiful Women</li>
                    </ul>
                </div>
            </div>
        </div>
    )
}