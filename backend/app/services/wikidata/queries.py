SPARQL_PLAYERS_QUERY = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX bd: <http://www.bigdata.com/rdf#>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?player ?playerLabel ?alias ?positionLabel ?birthDate ?nbaStart ?nbaEnd
WHERE {
  ?player wdt:P31 wd:Q5;
          wdt:P106 wd:Q3665646;
          wdt:P54 ?team.
  ?team wdt:P118 wd:Q155223.

  OPTIONAL { ?player wdt:P413 ?position. }
  OPTIONAL { ?player wdt:P569 ?birthDate. }
  OPTIONAL {
    ?player p:P54 ?membership.
    ?membership ps:P54 ?team2.
    ?team2 wdt:P118 wd:Q155223.
    OPTIONAL { ?membership pq:P580 ?nbaStart. }
    OPTIONAL { ?membership pq:P582 ?nbaEnd. }
  }
  OPTIONAL { ?player skos:altLabel ?alias FILTER (lang(?alias) = "en") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT __LIMIT__
OFFSET __OFFSET__
"""
