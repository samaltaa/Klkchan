import Image from "next/image";
import BoardList from "./components/BoardList";
import PopularThreads from "./components/PopularThreads";

export default function Home() {
  //
  return (

    <>
      <BoardList/>
      <PopularThreads/>
    </>
  );
}
