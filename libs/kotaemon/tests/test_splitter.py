from llama_index.core.schema import NodeRelationship

from kotaemon.base import Document
from kotaemon.indices.splitters import TokenSplitter

source1 = Document(
    content="The City Hall and Raffles Place MRT stations are paired cross-platform "
    "interchanges on the North–South line (NSL) and East–West line (EWL) of the "
    "Singapore Mass Rapid Transit (MRT) system. Both are situated in the Downtown "
    "Core district: City Hall station is near landmarks such as the former City Hall, "
    "St Andrew's Cathedral and the Padang, while Raffles Place station serves Merlion "
    "Park, The Fullerton Hotel and the Asian Civilisations Museum. The stations were "
    "first announced in 1982. Constructing the tunnels between the City Hall and "
    "Raffles Place stations required the draining of the Singapore River. The "
    "stations opened on 12 December 1987 as part of the MRT extension to Outram Park "
    "station. Cross-platform transfers between the NSL and EWL began on 28 October "
    "1989, ahead of the split of the MRT network into two lines. Both stations are "
    "designated Civil Defence shelters. City Hall station features a mural by Simon"
    "Wong which depicts government buildings in the area, while two murals at Raffles "
    "Place station by Lim Sew Yong and Thang Kiang How depict scenes of Singapore's "
    "history"
)

source2 = Document(
    content="The pink cockatoo (Cacatua leadbeateri) is a medium-sized cockatoo that "
    "inhabits arid and semi-arid inland areas across Australia, with the exception of "
    "the north east. The bird has a soft-textured white and salmon-pink plumage and "
    "large, bright red and yellow crest. The sexes are quite similar, although males "
    "are usually bigger while the female has a broader yellow stripe on the crest and "
    "develops a red eye when mature. The pink cockatoo is usually found in pairs or "
    "small groups, and feeds both on the ground and in trees. It is listed as an "
    "endangered species by the Australian government. Formerly known as Major "
    "Mitchell's cockatoo, after the explorer Thomas Mitchell, the species was "
    "officially renamed the pink cockatoo in 2023 by BirdLife Australia in light of "
    "Mitchell's involvement in the massacre of Aboriginal people at Mount Dispersion, "
    "as well as a general trend to make Australian species names more culturally "
    "inclusive. This pink cockatoo with a raised crest was photographed near Mount "
    "Grenfell in New South Wales."
)


def test_split_token():
    """Test that it can split tokens successfully"""
    splitter = TokenSplitter(chunk_size=30, chunk_overlap=10)
    chunks = splitter([source1, source2])

    assert isinstance(chunks, list), "Chunks should be a list"
    assert isinstance(chunks[0], Document), "Chunks should be a list of Documents"

    assert chunks[0].relationships[NodeRelationship.SOURCE].node_id == source1.doc_id
    assert (
        chunks[1].relationships[NodeRelationship.PREVIOUS].node_id == chunks[0].doc_id
    )
    assert chunks[1].relationships[NodeRelationship.NEXT].node_id == chunks[2].doc_id
    assert chunks[-1].relationships[NodeRelationship.SOURCE].node_id == source2.doc_id
